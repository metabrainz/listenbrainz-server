from messybrainz import db
import logging


def create_entity_clusters(create_without_anomalies, create_with_anomalies):
    """Takes two functions which create clusters for a given entity.

    Args:
        create_without_anomalies(function): this functions is responsible for creating
        clusters without considering anomalies.
        create_with_anomalies(function): this function will create clusters for the
        anomalies (A single MSID pointing to multiple MBIDs in entity_redirect table).

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_added_to_redirect (int): number of clusters added to redirect table.
    """

    clusters_modified = 0
    clusters_added_to_redirect = 0

    with db.engine.connect() as connection:
        clusters_modified, clusters_added_to_redirect = create_without_anomalies(connection)
        clusters_added_to_redirect += create_with_anomalies(connection)

    return clusters_modified, clusters_added_to_redirect


def create_entity_clusters_for_anomalies(connection,
                                        fetch_entities_left_to_cluster,
                                        get_entity_gids_from_recording_json_using_mbids,
                                        get_cluster_id_using_msid,
                                        link_entity_mbid_to_entity_cluster_id,
                                        get_recordings_metadata_using_entity_mbid):
    """Creates entity clusters for the anomalies (A single MSID pointing
       to multiple MBIDs in entity_redirect table).

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        fetch_entities_left_to_cluster(function): Returns mbids for the entity MBIDs that
                                                were not clustered after executing the
                                                first phase of clustering (clustering without
                                                considering anomalies). These are anomalies
                                                (A single MSID pointing to multiple MBIDs in
                                                entity_redirect table).
        get_entity_gids_from_recording_json_using_mbids(function): Returns entity MSIDs using
                                                                an entity MBID.
        get_cluster_id_using_msid(function): Gets the cluster ID for a given MSID.
        link_entity_mbid_to_entity_cluster_id(function): Links the entity mbid to the cluster_id.
        get_recordings_metadata_using_entity_mbid(function): gets recordings metadata using given MBID.

    Returns:
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    logger = logging.getLogger(__name__)
    logger_level = logger.getEffectiveLevel()

    logger.info("Creating clusters for anomalies...")
    clusters_add_to_redirect = 0
    entities_left = fetch_entities_left_to_cluster(connection)
    for entity_mbid in entities_left:
        entity_gids = get_entity_gids_from_recording_json_using_mbids(connection, entity_mbid)
        cluster_ids = {get_cluster_id_using_msid(connection, entity_gid) for entity_gid in entity_gids}
        for cluster_id in cluster_ids:
            link_entity_mbid_to_entity_cluster_id(connection, cluster_id, entity_mbid)
            clusters_add_to_redirect += 1
            logger.info("=" * 80)
            logger.info("Cluster ID: {0}\n".format(cluster_id))
            if logger_level == logging.DEBUG:
                if isinstance(entity_mbid, list):
                    mbids_str_list = [str(mbid) for mbid in entity_mbid]
                    mbids_str = ', '.join(mbids_str_list)
                else:
                    mbids_str = str(entity_mbid)
                logger.debug("Cluster MBID: {0}\n".format(mbids_str))
            logger.info("Recordings:")
            if logger_level >= logging.DEBUG:
                recordings = get_recordings_metadata_using_entity_mbid(connection, entity_mbid)
                if logger_level == logging.INFO:
                    formatted_rec = _format_recordings(recordings)
                else:
                    formatted_rec = _format_recordings(recordings, uuids=True)
                logger.info("{0}".format(formatted_rec))

    logger.info("\nClusters added to redirect table: {0}.".format(clusters_add_to_redirect))
    return clusters_add_to_redirect


def create_entity_clusters_without_considering_anomalies(connection,
                                                        fetch_unclustered_entity_mbids,
                                                        fetch_unclustered_gids_for_entity_mbids,
                                                        get_entity_cluster_id_using_entity_mbids,
                                                        link_entity_mbids_to_entity_cluster_id,
                                                        insert_entity_cluster,
                                                        get_recordings_metadata_using_entity_mbid):
    """Creates cluster for entity without considering anomalies (A single MSID pointing
       to multiple MBIDs in entity_redirect table).

    Args:
        connection: the sqlalchemy db connection to be used to execute queries.
        fetch_unclustered_entity_mbids (function): Fetch all the distinct entity
                                                MBIDs we have in recording_json table
                                                but don't have their corresponding MSIDs
                                                in entity_cluster table.
        fetch_unclustered_gids_for_entity_mbids (function): Fetches the gids corresponding
                                                        to an entity_mbid that are not present
                                                        in entity_cluster table.
        get_entity_cluster_id_using_entity_mbids (function): Returns the entity_cluster_id
                                                            that corresponds to the given entity MBID.
        link_entity_mbids_to_entity_cluster_id (function): Links the entity mbid to the cluster_id.
        insert_entity_cluster (function): Creates a cluster with given cluster_id in the
                                        entity_cluster table.
        get_recordings_metadata_using_entity_mbid(function): gets recordings metadata using given MBID.

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_added_to_redirect (int): number of clusters added to redirect table.
    """

    logger = logging.getLogger(__name__)
    logger_level = logger.getEffectiveLevel()

    logger.info("\nCreating clusters without considering anomalies...")
    clusters_modified = 0
    clusters_added_to_redirect = 0
    distinct_entity_mbids = fetch_unclustered_entity_mbids(connection)
    for entity_mbids in distinct_entity_mbids:
        gids = fetch_unclustered_gids_for_entity_mbids(connection, entity_mbids)
        if gids:
            cluster_id = get_entity_cluster_id_using_entity_mbids(connection, entity_mbids)
            if not cluster_id:
                cluster_id = gids[0]
                link_entity_mbids_to_entity_cluster_id(connection, cluster_id, entity_mbids)
                clusters_added_to_redirect +=1
            insert_entity_cluster(connection, cluster_id, gids)
            clusters_modified += 1
            logger.info("=" * 80)
            logger.info("Cluster ID: {0}\n".format(cluster_id))
            if logger_level == logging.DEBUG:
                if isinstance(entity_mbids, list):
                    mbids_str_list = [str(mbid) for mbid in entity_mbids]
                    mbids_str = ', '.join(mbids_str_list)
                else:
                    mbids_str = str(entity_mbids)
                logger.debug("Cluster MBID: {0}\n".format(mbids_str))
            logger.info("Number of entity added to this cluster: {0}.\n".format(len(gids)))
            logger.info("Recordings:")
            if logger_level >= logging.DEBUG:
                recordings = get_recordings_metadata_using_entity_mbid(connection, entity_mbids)
                if logger_level == logging.INFO:
                    formatted_rec = _format_recordings(recordings)
                else:
                    formatted_rec = _format_recordings(recordings, uuids=True)
                logger.info("{0}".format(formatted_rec))
    logger.info("\nClusters modified: {0}.".format(clusters_modified))
    logger.info("Clusters added to redirect table: {0}.\n".format(clusters_added_to_redirect))

    return clusters_modified, clusters_added_to_redirect


def _format_recordings(recordings, uuids=False):
    """ Returns string of formatted recordings in a human readable format.
            artist: <artist name>,
            release: <release title>,
            title: <recording title>,
            artist_mbids : <artist_mbids>,
            recording_mbids: <recording_mbids>,
            release_mbids: <release_mbids>
    """

    formatted_recordings = []
    for recording in recordings:
        rec_dict = {
            "artist" : recording["artist"],
            "title" : recording["title"],
            "release": recording.get("release", "")
        }
        if uuids:
            rec_dict["artist_mbids"] = recording.get("artist_mbids", "")
            rec_dict["recording_mbid"] = recording.get("recording_mbid", "")
            rec_dict["release_mbid"] = recording.get("release_mbid", "")

        formatted_recordings.append(rec_dict)

    rec_str = ""
    for rec in formatted_recordings:
        rec_str += "\nartist: {0}\nrelease: {1}\ntitle: {2}\n".format(rec["artist"],
                                                                rec.get("release", ""),
                                                                rec["title"])
        if uuids:
            artist_mbids_str = ', '.join(rec.get("artist_mbids"))
            rec_str += "artist_mbids: {0}\nrecording_mbid: {1}\nrelease_mbid: {2}\n".format(
                                                                artist_mbids_str,
                                                                rec.get("recording_mbid"),
                                                                rec.get("release_mbid")
            )
        rec_str += "-" * 80

    return rec_str
