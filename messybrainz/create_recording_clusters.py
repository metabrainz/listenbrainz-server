from messybrainz import db
from sqlalchemy import text
import uuid

# lifted from AcousticBrainz
def is_valid_uuid(u):
    try:
        u = uuid.UUID(u)
        return True
    except ValueError:
        return False


def insert_recording_cluster(connection, cluster_id, recording_gids):
    """Creates new cluster in the recording_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id (UUID): the recording MSID which will represent the cluster.
        recording_gids (list): the list of MSIDs will form a cluster.

    Returns:
        True if a new value is added to cluster otherwise False is returned.
    """

    query = text("""INSERT INTO recording_cluster (cluster_id, recording_gid, updated)
                         VALUES (:cluster_id, :recording_gid, now())
    """)
    cluster_modified = False
    for recording_gid in recording_gids:
        if not is_recording_cluster_present_in_recording_cluster(connection, cluster_id, recording_gid):
            connection.execute(query, {
                "cluster_id": cluster_id,
                "recording_gid": recording_gid,
                }
            )
            cluster_modified = True
    return cluster_modified


def fetch_gids_for_recording_mbid(connection, recording_mbid):
    """Fetches the gids corresponding to a recording_mbid.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        recording_mbid (UUID): the recording MBID for which gids are to be fetched.

    Returns:
        List of gids.
    """

    query = text("""SELECT gid
                      FROM recording_json
                      JOIN recording
                        ON recording_json.id = recording.data
                     WHERE recording_json.data ->> 'recording_mbid' = :recording_mbid
    """)
    gids = connection.execute(query, {
        "recording_mbid": recording_mbid,
        }
    )
    return [gid[0] for gid in gids]


def fetch_distinct_recording_mbids(connection):
    """Fetch all the distinct recording MBIDs we have in recording_json table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries

    Returns:
        recording_mbids.
    """

    query = text("""SELECT DISTINCT data ->> 'recording_mbid' AS recording_mbids
                               FROM recording_json 
                              WHERE data ->> 'recording_mbid' IS NOT NULL
                """)
    recording_mbids = connection.execute(query)
    return recording_mbids


def link_recording_mbid_to_recording_msid(connection, cluster_id, mbid):
    """Links the recording mbid to the cluster_id.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id: the gid which represents the cluster.
        mbid: mbid for the cluster.

    Returns:
        True if link is inserted into the cluster otherwise False is returned.
    """

    cluster_added = False
    if not is_recording_cluster_present_in_recording_redirect(connection, cluster_id, mbid):
        query = text("""INSERT INTO recording_redirect (recording_cluster_id, recording_mbid)
                            VALUES (:cluster_id, :mbid)
                    """)
        connection.execute(query, {
            "cluster_id": cluster_id,
            "mbid": mbid,
        })
        cluster_added = True
    return cluster_added


def is_recording_cluster_present_in_recording_redirect(connection, cluster_id, mbid):
    """Checks if recording cluster is already present in the recording_redirect table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id: the gid which represents the cluster.
        mbid: mbid for the cluster.

    Returns:
        True if cluster already present in recording_redirect table otherwise 
        False is returned.
    """

    query = text("""SELECT recording_cluster_id, recording_mbid
                      FROM recording_redirect
                     WHERE recording_cluster_id = :recording_cluster_id
                       AND recording_mbid = :recording_mbid
    """)
    result = connection.execute(query, {
        "recording_cluster_id": cluster_id,
        "recording_mbid": mbid,
    })
    if result.rowcount:
        return True
    return False


def is_recording_cluster_present_in_recording_cluster(connection, cluster_id, gid):
    """Checks if recording cluster is present in the recording_cluster table.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        cluster_id: the gid which represents the cluster.
        gid: gid for a recording.

    Returns:
        True if cluster present in recording_cluster table otherwise 
        False is returned.
    """

    query = text("""SELECT cluster_id, recording_gid
                      FROM recording_cluster
                     WHERE cluster_id = :cluster_id
                       AND recording_gid = :recording_gid
    """)
    result = connection.execute(query, {
        "cluster_id": cluster_id,
        "recording_gid": gid,
    })
    if result.rowcount:
        return True
    return False


def truncate_tables(connection):
    """Truncates recording_cluster and recording_redirect tables."""

    query = text("TRUNCATE TABLE recording_cluster")
    connection.execute(query)
    query = text("TRUNCATE TABLE recording_redirect")
    connection.execute(query)


def msid_processed(connection):
    """Returns the number of MSIDs processed by this script."""

    query = text("SELECT COUNT(*) FROM recording_cluster")
    result = connection.execute(query)
    num_msid = result.fetchone()
    return num_msid[0]


def create_recording_clusters(reset=False):
    """Creates clusters for recording mbids present in the recording_json table.

    Args:
        reset (boolean): should recording_cluster and recording_redirect tables be
                         truncated before creating clusters or not. 
    Returns:
        clusters_modified (int): number of clusters modified by the script.
        clusters_add_to_redirect (int): number of clusters added to redirect table.
        num_msid_processed (int): number of MSIDs processed by the script.
    """

    clusters_modified = 0
    clusters_add_to_redirect = 0
    num_msid_processed = 0
    with db.engine.begin() as connection:
        if reset:
            truncate_tables(connection)
        recording_mbids = fetch_distinct_recording_mbids(connection) 
        for recording_mbid in recording_mbids:
            if is_valid_uuid(recording_mbid[0]):
                gids = fetch_gids_for_recording_mbid(connection, recording_mbid[0])
                if insert_recording_cluster(connection, gids[0], gids):
                    clusters_modified += 1
                if link_recording_mbid_to_recording_msid(connection, gids[0], recording_mbid[0]):
                    clusters_add_to_redirect += 1
        num_msid_processed = msid_processed(connection)

    return clusters_modified, clusters_add_to_redirect, num_msid_processed
