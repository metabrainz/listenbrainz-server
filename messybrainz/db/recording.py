from messybrainz import db
from sqlalchemy import text


def insert_recording_cluster(connection, cluster_id, recording_gids):
    """Creates new cluster in the recording_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id (UUID): the recording MSID which will represent the cluster.
        recording_gids (list): the list of MSIDs will form a cluster.
    """

    values = [
        {"cluster_id": cluster_id, "recording_gid": recording_gid} for recording_gid in recording_gids
    ]

    connection.execute(text("""
        INSERT INTO recording_cluster (cluster_id, recording_gid, updated)
             VALUES (:cluster_id, :recording_gid, now())
    """), values
    )


def fetch_unclustered_gids_for_recording_mbid(connection, recording_mbid):
    """Fetches the gids corresponding to a recording_mbid that are
       not present in recording_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        recording_mbid (UUID): the recording MBID for which gids are to be fetched.

    Returns:
        List of gids.
    """

    gids = connection.execute(text("""
        SELECT r.gid
          FROM recording_json AS rj
          JOIN recording AS r
            ON rj.id = r.data
     LEFT JOIN recording_cluster AS rc
            ON r.gid = rc.recording_gid
         WHERE rj.data ->> 'recording_mbid' = :recording_mbid
           AND rc.recording_gid IS NULL
    """), {
        "recording_mbid": recording_mbid,
    })

    return [gid[0] for gid in gids]


def fetch_distinct_recording_mbids(connection):
    """Fetch all the distinct recording MBIDs we have in recording_json table
       but don't have their corresponding MSIDs in recording_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        recording_mbids(list): list of recording MBIDs.
    """

    recording_mbids = connection.execute(text("""
        SELECT DISTINCT rj.data ->> 'recording_mbid'
                   FROM recording_json AS rj
              LEFT JOIN recording_cluster AS rc
                     ON (rj.data ->> 'recording_mbid')::uuid = rc.recording_gid
                  WHERE rj.data ->> 'recording_mbid' IS NOT NULL
                    AND rc.recording_gid IS NULL
    """))

    return [recording_mbid[0] for recording_mbid in recording_mbids]


def link_recording_mbid_to_recording_msid(connection, cluster_id, mbid):
    """Links the recording mbid to the cluster_id.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id: the gid which represents the cluster.
        mbid: mbid for the cluster.
    """

    connection.execute(text("""
        INSERT INTO recording_redirect (recording_cluster_id, recording_mbid)
             VALUES (:cluster_id, :mbid)
    """), {
        "cluster_id": cluster_id,
        "mbid": mbid,
    })


def truncate_recording_cluster_and_recording_redirect_table():
    """Truncates recording_cluster and recording_redirect tables."""

    with db.engine.begin() as connection:
        connection.execute(text("""TRUNCATE TABLE recording_cluster"""))
        connection.execute(text("""TRUNCATE TABLE recording_redirect"""))


def get_recording_cluster_id_using_recording_mbid(connection, recording_mbid):
    """Returns cluster_id for a required recording MBID.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        recording_mbid (UUID): recording MBID for the cluster.

    Returns:
        cluster_id (UUID): MSID that represents the cluster if it exists else None.
    """

    cluster_id = connection.execute(text("""
        SELECT recording_cluster_id
          FROM recording_redirect
         WHERE recording_mbid = :recording_mbid
    """), {
        "recording_mbid": recording_mbid
    })

    if cluster_id.rowcount:
        return cluster_id.fetchone()['recording_cluster_id']
    else:
        return None


def create_recording_clusters():
    """Creates clusters for recording mbids present in the recording_json table.

    Returns:
        clusters_modified (int): number of clusters modified by the script.
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    clusters_modified = 0
    clusters_add_to_redirect = 0
    with db.engine.begin() as connection:
        recording_mbids = fetch_distinct_recording_mbids(connection)
        for recording_mbid in recording_mbids:
            gids = fetch_unclustered_gids_for_recording_mbid(connection, recording_mbid)
            if gids:
                cluster_id = get_recording_cluster_id_using_recording_mbid(connection, recording_mbid)
                if not cluster_id:
                    cluster_id = gids[0]
                    link_recording_mbid_to_recording_msid(connection, cluster_id, recording_mbid)
                    clusters_add_to_redirect +=1
                insert_recording_cluster(connection, cluster_id, gids)
                clusters_modified += 1

    return clusters_modified, clusters_add_to_redirect
