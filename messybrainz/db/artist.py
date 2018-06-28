
import brainzutils.musicbrainz_db.recording as mb_recording

from brainzutils import musicbrainz_db
from brainzutils.musicbrainz_db.exceptions import NoDataFoundException
from messybrainz import db
from messybrainz.db import data
from sqlalchemy import text


def insert_artist_mbids(connection, recording_mbid, artist_mbids):
    """ Inserts the artist_mbids corresponding to the recording_mbids
        into the recording_artist_join table.
    """

    query = text("""INSERT INTO recording_artist_join (recording_mbid, artist_mbid, updated)
                         VALUES (:recording_mbid, :artist_mbid, now())""")

    values = [
        {"recording_mbid": recording_mbid, "artist_mbid": artist_mbid} for artist_mbid in artist_mbids
    ]

    connection.execute(query, values)


def fetch_artist_mbids(connection, recording_mbid):
    """ Fetches artist MBIDs from the MusicBrainz database for the recording MBID.
    """

    recording = mb_recording.get_recording_by_mbid(recording_mbid, includes=['artists'])
    return [artist['id'] for artist in recording['artists']]


def fetch_recording_mbids_not_in_recording_artist_join(connection):
    """ Fetches recording MBIDs that are present in recording_json table
        but are not present in recording_artist_join table and returns
        a list of those recording MBIDs.
    """

    query = text("""SELECT DISTINCT rj.data ->> 'recording_mbid'
                               FROM recording_json AS rj
                          LEFT JOIN recording_artist_join AS raj
                                 ON (rj.data ->> 'recording_mbid')::uuid = raj.recording_mbid
                              WHERE rj.data ->> 'recording_mbid' IS NOT NULL
                                AND raj.recording_mbid IS NULL
    """)

    result = connection.execute(query)

    return [mbid[0] for mbid in result]


def truncate_recording_artist_join():
    """Truncates the table recording_artist_join."""

    with db.engine.begin() as connection:
        query = text("""TRUNCATE TABLE recording_artist_join""")
        connection.execute(query)


def get_artist_mbids_for_recording_mbid(connection, recording_mbid):
    """Returns list of artist MBIDs for a corresponding recording MBID
       in recording_artist_join table if recording MBID exists else None
       is returned.
    """

    query = text("""SELECT artist_mbid
                      FROM recording_artist_join
                     WHERE recording_mbid = :recording_mbid
    """)

    result = connection.execute(query, {"recording_mbid": recording_mbid})

    if result.rowcount:
        return [artist_mbid[0] for artist_mbid in result]
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
        INSERT INTO artist_credit_redirect (artist_credit_cluster_id, artist_mbids_array)
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
         WHERE artist_mbids_array = array_sort(:artist_credit_mbids)
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
                     ON convert_json_array_to_sorted_uuid_array(rj.data -> 'artist_mbids') = acr.artist_mbids_array
                  WHERE rj.data ->> 'artist_mbids' IS NOT NULL
                    AND acr.artist_mbids_array IS NULL
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
        SELECT artist_mbids_array
          FROM artist_credit_redirect
         WHERE artist_credit_cluster_id = :cluster_id
    """), {
        "cluster_id": cluster_id,
    })

    if mbids.rowcount:
        return [mbid[0] for mbid in mbids]

    return None


def create_artist_credit_clusters_without_considering_anomalies(connection):
    """Creates cluster for artist_credit without considering anomalies (A single MSID
       pointing to multiple MBIDs arrays in artist_credit_redirect table).

    Args:
        connection: the sqlalchemy db connection to be used to execute queries.

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    clusters_modified = 0
    clusters_add_to_redirect = 0
    with db.engine.begin() as connection:
        distinct_artist_credit_mbids = fetch_unclustered_distinct_artist_credit_mbids(connection)
        for artist_credit_mbids in distinct_artist_credit_mbids:
            gids = fetch_unclustered_gids_for_artist_credit_mbids(connection, artist_credit_mbids)
            if gids:
                cluster_id = get_artist_cluster_id_using_artist_mbids(connection, artist_credit_mbids)
                if not cluster_id:
                    cluster_id = gids[0]
                    link_artist_mbids_to_artist_credit_cluster_id(connection, cluster_id, artist_credit_mbids)
                    clusters_add_to_redirect +=1
                insert_artist_credit_cluster(connection, cluster_id, gids)
                clusters_modified += 1
    return clusters_modified, clusters_add_to_redirect


def create_artist_credit_clusters_for_anomalies(connection):
    """Creates artist_credit clusters for the anomalies (A single MSID
       pointing to multiple MBIDs arrays in artist_credit_redirect table).

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    clusters_add_to_redirect = 0
    artist_credits_left = fetch_artist_credits_left_to_cluster(connection)
    for artist_credit_mbids in artist_credits_left:
        artist_gids = get_artist_gids_from_recording_json_using_mbids(connection, artist_credit_mbids)
        cluster_ids = {get_cluster_id_using_msid(connection, artist_gid) for artist_gid in artist_gids}
        for cluster_id in cluster_ids:
            link_artist_mbids_to_artist_credit_cluster_id(connection, cluster_id, artist_credit_mbids)
            clusters_add_to_redirect += 1

    return clusters_add_to_redirect


def create_artist_credit_clusters():
    """Creates clusters for artist mbids present in the recording_json table.

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    with db.engine.begin() as connection:
        clusters_modified, clusters_add_to_redirect = create_artist_credit_clusters_without_considering_anomalies(connection)
        clusters_add_to_redirect += create_artist_credit_clusters_for_anomalies(connection)

    return clusters_modified, clusters_add_to_redirect
