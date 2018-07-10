from brainzutils.musicbrainz_db.exceptions import NoDataFoundException
from messybrainz import db
from sqlalchemy import text
import brainzutils.musicbrainz_db.release as mb_release
import logging
import messybrainz.db.common as db_common


def insert_release_cluster(connection, cluster_id, release_gids):
    """Creates new cluster in the release_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id (UUID): the release MSID which will represent the cluster.
        release_gids (list): the list of MSIDs which will form a cluster.
    """

    values = [
        {"cluster_id": cluster_id, "release_gid": release_gid} for release_gid in release_gids
    ]

    connection.execute(text("""
        INSERT INTO release_cluster (cluster_id, release_gid, updated)
             VALUES (:cluster_id, :release_gid, now())
        """), values
        )


def insert_releases_to_recording_release_join(connection, recording_mbid, releases):
    """ Inserts the releases corresponding to the recording_mbid
        into the recording_release_join table.
    """

    values = [
        {
            "recording_mbid": recording_mbid,
            "release_mbid": release['id'],
            "release_name": release['name'],
        } for release in releases
    ]

    connection.execute(text("""
        INSERT INTO recording_release_join (recording_mbid, release_mbid, release_name, updated)
             VALUES (:recording_mbid, :release_mbid, :release_name, now())
    """), values
    )


def fetch_unclustered_gids_for_release_mbid(connection, release_mbid):
    """Fetches the gids corresponding to a release_mbid that are
       not present in release_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        release_mbid (UUID): the release MBID for which gids are to be fetched.

    Returns:
        List of gids.
    """

    gids = connection.execute(text("""
        SELECT DISTINCT rec.release
                   FROM recording_json AS recj
                   JOIN recording AS rec
                     ON recj.id = rec.data
              LEFT JOIN release_cluster AS relc
                     ON rec.release = relc.release_gid
                  WHERE recj.data ->> 'release_mbid' = :release_mbid
                    AND relc.release_gid IS NULL
    """), {
        "release_mbid": release_mbid,
    })

    return [gid[0] for gid in gids]


def fetch_unclustered_distinct_release_mbids(connection):
    """Fetch all the distinct release MBIDs we have in recording_json table
       but don't have their corresponding MSIDs in release_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        release_mbids(list): list of release MBIDs.
    """

    release_mbids = connection.execute(text("""
        SELECT DISTINCT recj.data ->> 'release_mbid'
                   FROM recording_json AS recj
                   JOIN recording AS rec
                     ON rec.data = recj.id
              LEFT JOIN release_cluster AS relc
                     ON rec.release = relc.release_gid
                  WHERE recj.data ->> 'release_mbid' IS NOT NULL
                    AND relc.release_gid IS NULL
    """))

    return [release_mbid[0] for release_mbid in release_mbids]


def link_release_mbid_to_release_msid(connection, cluster_id, mbid):
    """Links the release mbid to the cluster_id.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id: the gid which represents the cluster.
        mbid: mbid for the cluster.
    """

    connection.execute(text("""
        INSERT INTO release_redirect (release_cluster_id, release_mbid)
             VALUES (:cluster_id, :mbid)
    """), {
        "cluster_id": cluster_id,
        "mbid": mbid,
    })


def truncate_release_cluster_and_release_redirect_table():
    """Truncates release_cluster and release_redirect tables."""

    with db.engine.begin() as connection:
        connection.execute(text("""TRUNCATE TABLE release_cluster"""))
        connection.execute(text("""TRUNCATE TABLE release_redirect"""))


def get_release_cluster_id_using_release_mbid(connection, release_mbid):
    """Returns cluster_id for a required release MBID.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        release_mbid (UUID): release MBID for the cluster.

    Returns:
        cluster_id (UUID): MSID that represents the cluster if it exists else None.
    """

    cluster_id = connection.execute(text("""
        SELECT release_cluster_id
          FROM release_redirect
         WHERE release_mbid = :release_mbid
    """), {
        "release_mbid": release_mbid
    })

    if cluster_id.rowcount:
        return cluster_id.fetchone()['release_cluster_id']
    else:
        return None



def fetch_release_left_to_cluster(connection):
    """ Returns a list of release MBID for the release MBIDs that
        were not added to redirect table after executing
        the first phase of clustering. These are anomalies.
    """

    result = connection.execute(text("""
        SELECT DISTINCT recj.data ->> 'release_mbid'
                   FROM recording AS rec
                   JOIN recording_json AS recj
                     ON rec.data = recj.id
              LEFT JOIN release_redirect AS relr
                     ON (recj.data ->> 'release_mbid')::uuid = relr.release_mbid
                  WHERE recj.data ->> 'release_mbid' IS NOT NULL
                    AND relr.release_mbid IS NULL
    """))

    return [r[0] for r in result]


def get_release_gids_from_recording_json_using_mbid(connection, release_mbid):
    """Returns release MSIDs using a release MBID.
    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        release_mbid (UUID): a release MBID for which gids are to be fetched.
    Returns:
        gids(list): list of release gids for a given release MBID.
    """

    result = connection.execute(text("""
        SELECT DISTINCT r.release
                   FROM recording AS r
                   JOIN recording_json AS rj
                     ON r.data = rj.id
                  WHERE :release_mbid = (rj.data ->> 'release_mbid')::uuid
    """), {
        "release_mbid": release_mbid,
    })

    return [release_gid[0] for release_gid in result]


def get_cluster_id_using_msid(connection, msid):
    """ Gets the release cluster ID for a given release MSID.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        msid(UUID): a release gid for which cluster_id is to be fetched.

    Returns:
        cluster_id(UUID): cluster_id for the queried MSID if found. Else None is returned.
    """

    result = connection.execute(text("""
        SELECT cluster_id
          FROM release_cluster
         WHERE release_gid = :msid
    """), {
        "msid": msid,
    })

    if result.rowcount:
        return result.fetchone()[0]
    return None


def get_release_mbids_using_msid(connection, release_msid):
    """Returns a list of release MBIDs that corresponds
       to the given release MSID.
    """

    cluster_id = get_cluster_id_using_msid(connection, release_msid)
    if cluster_id is None:
        return None

    mbids = connection.execute(text("""
        SELECT release_mbid
          FROM release_redirect
         WHERE release_cluster_id = :cluster_id
    """), {
        "cluster_id": cluster_id,
    })

    if mbids.rowcount:
        return [mbid[0] for mbid in mbids]

    return None


def get_recordings_metadata_using_release_mbid(connection, mbid):
    """Returns the recording Metadata from recording_json table using release MBID."""

    recordings = connection.execute(text("""
        SELECT recording_json.data
          FROM recording_json
         WHERE (data ->> 'release_mbid')::uuid = :mbid
    """), {
        "mbid": mbid,
    })

    return [recording[0] for recording in recordings]


def create_release_clusters_without_considering_anomalies(connection):
    """Creates clusters for release MBIDs present in the recording_json table
       without considering anomalies.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        clusters_modified (int): number of clusters modified by the script.
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    return db_common.create_entity_clusters_without_considering_anomalies(connection,
        fetch_unclustered_distinct_release_mbids,
        fetch_unclustered_gids_for_release_mbid,
        get_release_cluster_id_using_release_mbid,
        link_release_mbid_to_release_msid,
        insert_release_cluster,
        get_recordings_metadata_using_release_mbid
    )


def create_release_clusters_for_anomalies(connection):
    """Creates clusters for release MBIDs present in the recording_json table
       considering anomalies.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    return db_common.create_entity_clusters_for_anomalies(connection,
        fetch_release_left_to_cluster,
        get_release_gids_from_recording_json_using_mbid,
        get_cluster_id_using_msid,
        link_release_mbid_to_release_msid,
        get_recordings_metadata_using_release_mbid
    )


def create_release_clusters():
    """Creates clusters for release MBIDs present in the recording_json table.

    Returns:
        clusters_modified (int): number of clusters modified by the script.
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    return db.common.create_entity_clusters(
        create_release_clusters_without_considering_anomalies,
        create_release_clusters_for_anomalies,
    )


def fetch_releases_from_musicbrainz_db(connection, recording_mbid):
    """ Fetches releases from the MusicBrainz database for the recording MBID
        and returns a list of releases which consists a dict with release MBID 
        and release name.
    """

    return mb_release.get_releases_using_recording_mbid(recording_mbid)


def fetch_recording_mbids_not_in_recording_release_join(connection):
    """ Fetches recording MBIDs that are present in recording_json table
        but are not present in recording_release_join table and returns
        a list of those recording MBIDs.
    """

    result = connection.execute(text("""
        SELECT DISTINCT recj.data ->> 'recording_mbid'
                   FROM recording_json AS recj
              LEFT JOIN recording_release_join AS rrj
                     ON (recj.data ->> 'recording_mbid')::uuid = rrj.recording_mbid
                  WHERE recj.data ->> 'recording_mbid' IS NOT NULL
                    AND rrj.recording_mbid IS NULL
    """))

    return [mbid[0] for mbid in result]


def truncate_recording_release_join():
    """Truncates the table recording_release_join."""

    with db.engine.begin() as connection:
        connection.execute(text("""TRUNCATE TABLE recording_release_join"""))


def get_releases_for_recording_mbid(connection, recording_mbid):
    """Returns list of releases for a corresponding recording MBID
       in recording_release_join table if recording MBID exists else
       empty list is returned.
    """

    result = connection.execute(text("""
        SELECT release_mbid, release_name
          FROM recording_release_join
         WHERE recording_mbid = :recording_mbid
    """), {"recording_mbid": recording_mbid}
    )

    return [(r['release_mbid'], r['release_name']) for r in result]


def fetch_and_store_releases_for_all_recording_mbids():
    """ Fetches releases from the musicbrainz database for the recording MBIDs
        in the recording_json table submitted while submitting a listen.
        Returns the number of recording MBIDs that were processed and number of
        recording MBIDs that were added to the recording_release_join table.
    """

    logger = logging.getLogger(__name__)
    logger_level = logger.getEffectiveLevel()

    with db.engine.begin() as connection:
        recording_mbids = fetch_recording_mbids_not_in_recording_release_join(connection)
        num_recording_mbids_added = 0
        num_recording_mbids_processed = len(recording_mbids)
        for recording_mbid in recording_mbids:
            try:
                releases = fetch_releases_from_musicbrainz_db(connection, recording_mbid)
                if logger_level == logging.DEBUG:
                    logger.debug("Recording MBID: {0}".format(recording_mbid))
                    logger.debug("Releases fetched:")
                    logger.debug("\t\tRelease MBID\t\t\t Release Name")
                    logger.debug("-" * 80)
                    for release in releases:
                        logger.debug("{0} : {1}".format(release["id"], release["name"]))
                    logger.debug("-" * 80)
                insert_releases_to_recording_release_join(connection, recording_mbid, releases)
                num_recording_mbids_added += 1
            except NoDataFoundException:
                # While submitting recordings we don't check if the recording MBID
                # exists in MusicBrainz database. So, this exception can get raised if
                # recording MBID doesnot exist in MusicBrainz database and we tried to
                # query for it. Or in case of standalone recordings we will get no releases
                # for a given recording MBID.
                pass

        return num_recording_mbids_processed, num_recording_mbids_added
