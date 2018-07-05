from messybrainz import db
from sqlalchemy import text
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
