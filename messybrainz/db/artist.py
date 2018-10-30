
import brainzutils.musicbrainz_db.recording as mb_recording
import messybrainz.db.common as db_common
from brainzutils import musicbrainz_db
from brainzutils.musicbrainz_db.exceptions import NoDataFoundException
from messybrainz import db
from messybrainz.db import data
from sqlalchemy import text
from uuid import UUID


def insert_artist_mbids(connection, recording_mbid, artist_mbids):
    """ Inserts the artist_mbids corresponding to the recording_mbids
        into the recording_artist_join table.
    """

    artist_mbids.sort()
    connection.execute(text("""
        INSERT INTO recording_artist_join (recording_mbid, artist_mbids, updated)
             VALUES (:recording_mbid, :artist_mbids, now())
    """), {
        "recording_mbid": recording_mbid,
        "artist_mbids": artist_mbids
    })


def fetch_artist_mbids(connection, recording_mbid):
    """ Fetches artist MBIDs from the MusicBrainz database for the recording MBID.
    """

    recording = mb_recording.get_recording_by_mbid(recording_mbid, includes=['artists'])
    return [UUID(artist['id']) for artist in recording['artists']]


def fetch_recording_mbids_not_in_recording_artist_join(connection):
    """ Fetches recording MBIDs that are present in recording_json table
        but are not present in recording_artist_join table and returns
        a list of those recording MBIDs.
    """

    result = connection.execute(text("""
        SELECT DISTINCT rj.data ->> 'recording_mbid'
                   FROM recording_json AS rj
              LEFT JOIN recording_artist_join AS raj
                     ON rj.data ->> 'recording_mbid' = (raj.recording_mbid)::text
                  WHERE rj.data ->> 'recording_mbid' IS NOT NULL
                    AND rj.data ->> 'recording_mbid' != ''
                    AND raj.recording_mbid IS NULL
    """))

    return [mbid[0] for mbid in result]


def truncate_recording_artist_join():
    """Truncates the table recording_artist_join."""

    with db.engine.begin() as connection:
        connection.execute(text("""TRUNCATE TABLE recording_artist_join"""))


def get_artist_mbids_for_recording_mbid(connection, recording_mbid):
    """Returns list of artist MBIDs for a corresponding recording MBID
       in recording_artist_join table if recording MBID exists else None
       is returned.
    """

    result = connection.execute(text("""
        SELECT artist_mbids
          FROM recording_artist_join
         WHERE recording_mbid = :recording_mbid
    """), {
        "recording_mbid": recording_mbid
    })

    if result.rowcount:
        return result.fetchone()['artist_mbids']
    else:
        return None


def fetch_and_store_artist_mbids_for_all_recording_mbids():
    """ Fetches artist MBIDs from the musicbrainz database for the recording MBIDs
        in the recording_json table submitted while submitting a listen.
        Returns the number of recording MBIDs that were processed and number of
        recording MBIDs that were added to the recording_artist_join table.
    """

    with db.engine.begin() as connection:
        recording_mbids = fetch_recording_mbids_not_in_recording_artist_join(connection)
        num_recording_mbids_added = 0
        num_recording_mbids_processed = len(recording_mbids)
        for recording_mbid in recording_mbids:
            try:
                artist_mbids = fetch_artist_mbids(connection, recording_mbid)
                insert_artist_mbids(connection, recording_mbid, artist_mbids)
                num_recording_mbids_added += 1
            except NoDataFoundException:
                # While submitting recordings we don't check if the recording MBID
                # exists in MusicBrainz database. So, this exception can get raised if
                # recording MBID doesnot exist in MusicBrainz database and we tried to
                # query for it.
                pass

        return num_recording_mbids_processed, num_recording_mbids_added


def fetch_unclustered_distinct_artist_credit_mbids(connection):
    """Fetch all the distinct artist MBIDs we have in recording_json table
       but don't have their corresponding MSIDs in artist_credit_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        artist_credit_mbids(list): List of artist MBIDs.
    """

    # convert_json_array_to_sorted_uuid_array is a custom function for implementation
    # details check admin/sql/create_functions.sql
    result = connection.execute(text("""
        SELECT DISTINCT convert_json_array_to_sorted_uuid_array(rj.data -> 'artist_mbids')
                   FROM recording_json AS rj
                   JOIN recording AS r
                     ON r.data = rj.id
              LEFT JOIN artist_credit_cluster AS acc
                     ON r.artist = acc.artist_credit_gid
                  WHERE rj.data ->> 'artist_mbids' IS NOT NULL
                    AND acc.artist_credit_gid IS NULL
    """))

    return [artist_credit_mbids[0] for artist_credit_mbids in result]


def link_artist_mbids_to_artist_credit_cluster_id(connection, cluster_id, artist_credit_mbids):
    """Links the artist mbids to the cluster_id.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id: the gid which represents the cluster.
        artist_credit_mbids (list): list of artist MBIDs for the cluster.
    """

    connection.execute(text("""
        INSERT INTO artist_credit_redirect (artist_credit_cluster_id, artist_mbids)
             VALUES (:cluster_id, array_sort(:artist_credit_mbids))
    """), {
        "cluster_id": cluster_id,
        "artist_credit_mbids": artist_credit_mbids,
    })


def truncate_artist_credit_cluster_and_redirect_tables():
    """Truncates artis_credit_cluster and artist_credit_redirect table."""

    with db.engine.begin() as connection:
        connection.execute(text("""TRUNCATE TABLE artist_credit_cluster"""))
        connection.execute(text("""TRUNCATE TABLE artist_credit_redirect"""))


def insert_artist_credit_cluster(connection, cluster_id, artist_credit_gids):
    """Creates a cluster with given cluster_id in the artist_credit_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id (UUID): the artist MSID which will represent the cluster.
        artist_credit_gids (list): the list of MSIDs which will form a cluster.
    """

    values = [
        {"cluster_id": cluster_id, "artist_credit_gid": artist_credit_gid} for artist_credit_gid in artist_credit_gids
    ]

    connection.execute(text("""
        INSERT INTO artist_credit_cluster (cluster_id, artist_credit_gid, updated)
             VALUES (:cluster_id, :artist_credit_gid, now())
    """), values
    )


def fetch_unclustered_gids_for_artist_credit_mbids(connection, artist_credit_mbids):
    """Fetches the gids corresponding to an artist_mbid that are
       not present in artist_credit_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        artist_credit_mbids (list): a list of artist MBIDs for which gids are to be fetched.
                                    The list is first sorted and then query is done.

    Returns:
        gids(list): List of gids.
    """

    artist_credit_mbids.sort()
    # convert_json_array_to_sorted_uuid_array is a custom function for implementation
    # details check admin/sql/create_functions.sql
    gids = connection.execute(text("""
        SELECT DISTINCT r.artist
                   FROM recording_json AS rj
                   JOIN recording AS r
                     ON rj.id = r.data
              LEFT JOIN artist_credit_cluster AS acc
                     ON r.artist = acc.artist_credit_gid
                  WHERE :artist_credit_mbids = convert_json_array_to_sorted_uuid_array(rj.data -> 'artist_mbids')
                    AND acc.artist_credit_gid IS NULL
    """), {
        "artist_credit_mbids": artist_credit_mbids,
    })

    return [gid[0] for gid in gids]


def get_artist_cluster_id_using_artist_mbids(connection, artist_credit_mbids):
    """Returns the artist_credit_cluster_id that corresponds
       to the given artist MBIDs.
    """

    # array_sort is a custom function for implementation
    # details check admin/sql/create_functions.sql
    gid = connection.execute(text("""
        SELECT artist_credit_cluster_id
          FROM artist_credit_redirect
         WHERE artist_mbids = array_sort(:artist_credit_mbids)
    """), {
        "artist_credit_mbids": artist_credit_mbids,
    })

    if gid.rowcount:
        return gid.fetchone()[0]
    return None


def fetch_artist_credits_left_to_cluster(connection):
    """ Returns array of artist_mbids for the artist MBIDs that
        were not clustered after executing the first phase of clustering.
        These are anomalies (A single MSID pointing to multiple MBIDs arrays
        in artist_credit_redirect table).
    """

    # convert_json_array_to_sorted_uuid_array is a custom function for implementation
    # details check admin/sql/create_functions.sql
    result = connection.execute(text("""
        SELECT DISTINCT convert_json_array_to_sorted_uuid_array(rj.data -> 'artist_mbids')
                   FROM recording as r
                   JOIN recording_json AS rj
                     ON r.data = rj.id
              LEFT JOIN artist_credit_redirect AS acr
                     ON convert_json_array_to_sorted_uuid_array(rj.data -> 'artist_mbids') = acr.artist_mbids
                  WHERE rj.data ->> 'artist_mbids' IS NOT NULL
                    AND acr.artist_mbids IS NULL
    """))

    return [r[0] for r in result]


def get_cluster_id_using_msid(connection, msid):
    """ Gets the cluster ID for a given MSID.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        msid(UUID): an artist_credit gid for which cluster_id is to be fetched.

    Returns:
        cluster_id(UUID): cluster_id for the queried MSID if found. Else None is returned.
    """

    result = connection.execute(text("""
        SELECT DISTINCT cluster_id
                   FROM artist_credit_cluster
                  WHERE artist_credit_gid = :msid
    """), {
        "msid": msid
    })

    if result.rowcount:
        return result.fetchone()[0]
    return None


def get_artist_gids_from_recording_json_using_mbids(connection, artist_mbids):
    """Returns artist MSIDs using a list of artist MBIDs.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        artist_mbids (list): a list of artist MBIDs for which gids are to be fetched.

    Returns:
        gids(list): list of artist gids for a given array of artist MBIDs.
    """

    # convert_json_array_to_sorted_uuid_array is a custom function for implementation
    # details check admin/sql/create_functions.sql
    result = connection.execute(text("""
        SELECT DISTINCT r.artist
                   FROM recording AS r
                   JOIN recording_json AS rj
                     ON r.data = rj.id
                  WHERE array_sort(:artist_mbids) = convert_json_array_to_sorted_uuid_array(rj.data -> 'artist_mbids')
    """), {
        "artist_mbids": artist_mbids,
    })

    return [artist_gid[0] for artist_gid in result]


def get_artist_mbids_using_msid(connection, artist_msid):
    """Returns a list of list of artist MBIDs that corresponds
       to the given artist MSID.
    """

    cluster_id = get_cluster_id_using_msid(connection, artist_msid)
    # array_sort is a custom function for implementation
    # details check admin/sql/create_functions.sql
    mbids = connection.execute(text("""
        SELECT artist_mbids
          FROM artist_credit_redirect
         WHERE artist_credit_cluster_id = :cluster_id
    """), {
        "cluster_id": cluster_id,
    })

    if mbids.rowcount:
        return [mbid[0] for mbid in mbids]

    return None


def get_recordings_metadata_using_artist_mbids(connection, mbids):
    """Returns the recording Metadata from recording_json table using artist MBIDs."""

    # convert_json_array_to_sorted_uuid_array is a custom function for implementation
    # details check admin/sql/create_functions.sql
    recordings = connection.execute(text("""
        SELECT recording_json.data
          FROM recording_json
         WHERE convert_json_array_to_sorted_uuid_array(data -> 'artist_mbids') = :mbids
    """), {
        "mbids": mbids,
    })

    return [recording[0] for recording in recordings]


def create_artist_credit_clusters_without_considering_anomalies(connection):
    """Creates cluster for artist_credit without considering anomalies (A single MSID
       pointing to multiple MBIDs arrays in artist_credit_redirect table).

    Args:
        connection: the sqlalchemy db connection to be used to execute queries.

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    return db_common.create_entity_clusters_without_considering_anomalies(connection,
        fetch_unclustered_distinct_artist_credit_mbids,
        fetch_unclustered_gids_for_artist_credit_mbids,
        get_artist_cluster_id_using_artist_mbids,
        link_artist_mbids_to_artist_credit_cluster_id,
        insert_artist_credit_cluster,
        get_recordings_metadata_using_artist_mbids
    )


def create_artist_credit_clusters_for_anomalies(connection):
    """Creates artist_credit clusters for the anomalies (A single MSID
       pointing to multiple MBIDs arrays in artist_credit_redirect table).

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """
    return db_common.create_entity_clusters_for_anomalies(connection,
        fetch_artist_credits_left_to_cluster,
        get_artist_gids_from_recording_json_using_mbids,
        get_cluster_id_using_msid,
        link_artist_mbids_to_artist_credit_cluster_id,
        get_recordings_metadata_using_artist_mbids
    )


def create_artist_credit_clusters():
    """Creates clusters for artist mbids present in the recording_json table.

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_added_to_redirect (int): number of clusters added to redirect table.
    """

    return db.common.create_entity_clusters(
        create_artist_credit_clusters_without_considering_anomalies,
        create_artist_credit_clusters_for_anomalies,
    )


def fetch_unclustered_artist_mbids_using_recording_artist_join(connection):
    """ Fetches artist MBIDs from recording_artist_join table that don't
        have corresponding MSID in artsit_credit_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        artist_mbids(list): returns the list of artist MBIDs.
    """

    artist_mbids = connection.execute(text("""
        SELECT DISTINCT raj.artist_mbids
                   FROM recording_json AS rj
                   JOIN recording_artist_join AS raj
                     ON (rj.data ->> 'recording_mbid') = (raj.recording_mbid)::text
                   JOIN recording AS r
                     ON r.data = rj.id
              LEFT JOIN artist_credit_cluster AS acc
                     ON r.artist = acc.artist_credit_gid
                  WHERE acc.artist_credit_gid IS NULL
    """))

    return [artist_mbid[0] for artist_mbid in artist_mbids]


def fetch_unclustered_gids_for_artist_mbids_using_recording_artist_join(connection, artist_mbids):
    """Fetches the gids corresponding to artist_mbid that are
       not present in artist_credit_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        artist_mbids (list): a list of artist MBIDs for which gids are to be fetched.

    Returns:
        gids(list): List of gids.
    """

    artist_mbids.sort()
    gids = connection.execute(text("""
        SELECT DISTINCT r.artist
                   FROM recording_json AS rj
                   JOIN recording_artist_join AS raj
                     ON (rj.data ->> 'recording_mbid') = (raj.recording_mbid)::text
                   JOIN recording AS r
                     ON rj.id = r.data
              LEFT JOIN artist_credit_cluster AS acc
                     ON r.artist = acc.artist_credit_gid
                  WHERE :artist_mbids = raj.artist_mbids
                    AND acc.artist_credit_gid IS NULL
    """), {
        "artist_mbids": artist_mbids,
    })

    return [gid[0] for gid in gids]


def fetch_artist_mbids_left_to_cluster_from_recording_artist_join(connection):
    """ Returns array of artist_mbids for the artist MBIDs that
        were not clustered after executing the first phase of clustering using
        fetched artist MBIDs. These are anomalies (A single MSID pointing to
        multiple MBIDs arrays in artist_credit_redirect table).
    """

    result = connection.execute(text("""
        SELECT DISTINCT raj.artist_mbids
                   FROM recording AS r
                   JOIN recording_json AS rj
                     ON r.data = rj.id
                   JOIN recording_artist_join AS raj
                     ON (rj.data ->> 'recording_mbid') = (raj.recording_mbid)::text
              LEFT JOIN artist_credit_redirect AS acr
                     ON raj.artist_mbids = acr.artist_mbids
                  WHERE acr.artist_mbids IS NULL
    """))

    return [r[0] for r in result]


def get_gids_from_recording_using_fetched_artist_mbids(connection, artist_mbids):
    """ Returns artist gids from recording table using artist MBIDs and
        recording_artist_join table using a given list of artist MBIDs.
    """

    artist_mbids.sort()
    result = connection.execute(text("""
        SELECT DISTINCT r.artist
                   FROM recording AS r
                   JOIN recording_json AS rj
                     ON r.data = rj.id
                   JOIN recording_artist_join AS raj
                     ON rj.data ->> 'recording_mbid' = (raj.recording_mbid)::text
                  WHERE :artist_mbids = raj.artist_mbids
    """), {
        "artist_mbids": artist_mbids,
    })

    return [artist_gid[0] for artist_gid in result]


def get_recordings_metadata_using_artist_mbids_and_recording_artist_join(connection, mbids):
    """ Returns the recording Metadata from recording_json table using artist MBIDs and
        recording_artist_join.
    """

    recordings = connection.execute(text("""
        SELECT rj.data
          FROM recording_json AS rj
          JOIN recording_artist_join AS raj
            ON rj.data ->> 'recording_mbid' = (raj.recording_mbid)::text
         WHERE raj.artist_mbids = :mbids
    """), {
        "mbids": mbids,
    })

    return [recording[0] for recording in recordings]


def create_clusters_using_fetched_artist_mbids_without_anomalies(connection):
    """Creates cluster for artist_credit without considering anomalies (A single MSID
       pointing to multiple MBIDs arrays in artist_credit_redirect table). Using fetched
       artist MBIDs from recording_artist_join table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries.

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """
    return db.common.create_entity_clusters_without_considering_anomalies(connection,
        fetch_unclustered_artist_mbids_using_recording_artist_join,
        fetch_unclustered_gids_for_artist_mbids_using_recording_artist_join,
        get_artist_cluster_id_using_artist_mbids,
        link_artist_mbids_to_artist_credit_cluster_id,
        insert_artist_credit_cluster,
        get_recordings_metadata_using_artist_mbids_and_recording_artist_join,
    )


def create_clusters_using_fetched_artist_mbids_for_anomalies(connection):
    """Creates artist_credit clusters for the anomalies (A single MSID
       pointing to multiple MBIDs arrays in artist_credit_redirect table).
       Using fetched artist MBIDs from recording_artist_join table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    return db_common.create_entity_clusters_for_anomalies(connection,
        fetch_artist_mbids_left_to_cluster_from_recording_artist_join,
        get_gids_from_recording_using_fetched_artist_mbids,
        get_cluster_id_using_msid,
        link_artist_mbids_to_artist_credit_cluster_id,
        get_recordings_metadata_using_artist_mbids_and_recording_artist_join
    )


def create_clusters_using_fetched_artist_mbids():
    """ Creates clusters using the artist_mbids fetched from recording_artist_join
        table.

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_added_to_redirect (int): number of clusters added to redirect table.
    """

    return db.common.create_entity_clusters(
        create_clusters_using_fetched_artist_mbids_without_anomalies,
        create_clusters_using_fetched_artist_mbids_for_anomalies,
    )
