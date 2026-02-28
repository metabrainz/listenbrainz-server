from sqlalchemy import text


def get_recording_collections_for_editor(mb_connection, editor_id):
    """Get all recording collections for a given MB editor.

    Args:
        mb_connection: MB database connection.
        editor_id: The MB editor ID (integer) of the user.
    """
    query = text("""
        SELECT ec.gid::text, ec.name, ec.public, ec.description
          FROM editor_collection ec
          JOIN editor_collection_type ect ON ect.id = ec.type
         WHERE ec.editor = :editor_id
           AND ect.entity_type = 'recording'
         ORDER BY ec.name
    """)
    result = mb_connection.execute(query, {"editor_id": editor_id})
    return [
        {
            "gid": row["gid"],
            "name": row["name"],
            "public": row["public"],
            "description": row["description"],
        }
        for row in result.mappings()
    ]


def get_collection_recordings(mb_connection, collection_gid):
    """Get all recording MBIDs from a specific MB collection.

    Args:
        mb_connection: MB database connection.
        collection_gid: The UUID (string) of the collection.
    """
    query = text("""
        SELECT r.gid::text AS recording_mbid
          FROM editor_collection_recording ecr
          JOIN recording r ON r.id = ecr.recording
          JOIN editor_collection ec ON ec.id = ecr.collection
         WHERE ec.gid = CAST(:collection_gid AS uuid)
         ORDER BY ecr.position, ecr.added
    """)
    result = mb_connection.execute(query, {"collection_gid": collection_gid})
    return [row["recording_mbid"] for row in result.mappings()]


def get_collection_metadata(mb_connection, collection_gid):
    """Get metadata for a specific MB collection. It also verifies that the collection exists and is a recording collection.

    Args:
        mb_connection: MB database connection.
        collection_gid: The UUID (string) of the collection.
    """
    query = text("""
        SELECT ec.gid::text, ec.name, ec.public, ec.description, ec.editor AS editor_id
          FROM editor_collection ec
          JOIN editor_collection_type ect ON ect.id = ec.type
         WHERE ec.gid = CAST(:collection_gid AS uuid)
           AND ect.entity_type = 'recording'
    """)
    result = mb_connection.execute(query, {"collection_gid": collection_gid})
    row = result.mappings().first()
    if row is None:
        return None
    return {
        "gid": row["gid"],
        "name": row["name"],
        "public": row["public"],
        "description": row["description"],
        "editor_id": row["editor_id"],
    }
