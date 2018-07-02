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
                                        link_entity_mbid_to_entity_cluster_id):
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

    Returns:
        clusters_add_to_redirect (int): number of clusters added to redirect table.
    """

    logging.debug("Creating clusters for anomalies...")
    clusters_add_to_redirect = 0
    entities_left = fetch_entities_left_to_cluster(connection)
    for entity_mbid in entities_left:
        logging.debug("-" * 80)
        logging.debug("Cluster MBIDs:\n\t{0}".format(entity_mbid))
        entity_gids = get_entity_gids_from_recording_json_using_mbids(connection, entity_mbid)
        cluster_ids = {get_cluster_id_using_msid(connection, entity_gid) for entity_gid in entity_gids}
        logging.debug("Cluster IDs:")
        for cluster_id in cluster_ids:
            link_entity_mbid_to_entity_cluster_id(connection, cluster_id, entity_mbid)
            logging.debug("\t{0}".format(cluster_id))
            clusters_add_to_redirect += 1

    logging.debug("\nClusters added to redirect table: {0}.".format(clusters_add_to_redirect))
    return clusters_add_to_redirect


def create_entity_clusters_without_considering_anomalies(connection,
                                                        fetch_unclustered_entity_mbids,
                                                        fetch_unclustered_gids_for_entity_mbids,
                                                        get_entity_cluster_id_using_entity_mbids,
                                                        link_entity_mbids_to_entity_cluster_id,
                                                        insert_entity_cluster):
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

    Returns:
        clusters_modified (int): number of clusters modified.
        clusters_added_to_redirect (int): number of clusters added to redirect table.
    """

    logging.debug("\nCreating clusters without considering anomalies...")
    clusters_modified = 0
    clusters_added_to_redirect = 0
    distinct_entity_mbids = fetch_unclustered_entity_mbids(connection)
    for entity_mbids in distinct_entity_mbids:
        logging.debug("-" * 80)
        logging.debug("Cluster MBIDs:\n\t{0}".format(entity_mbids))
        gids = fetch_unclustered_gids_for_entity_mbids(connection, entity_mbids)
        if gids:
            cluster_id = get_entity_cluster_id_using_entity_mbids(connection, entity_mbids)
            if not cluster_id:
                cluster_id = gids[0]
                logging.debug("Cluster ID:\n\t{0}".format(cluster_id))
                link_entity_mbids_to_entity_cluster_id(connection, cluster_id, entity_mbids)
                clusters_added_to_redirect +=1
            insert_entity_cluster(connection, cluster_id, gids)
            logging.debug("Cluster gids:")
            for gid in gids:
                logging.debug("\t{0}".format(gid))
            clusters_modified += 1
    logging.debug("\nClusters modified: {0}.".format(clusters_modified))
    logging.debug("Clusters added to redirect table: {0}.\n".format(clusters_added_to_redirect))

    return clusters_modified, clusters_added_to_redirect
