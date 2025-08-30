from sqlalchemy import text

def search_ia_tracks(db_conn, artist=None, track=None, album=None):
    """
    Search the internetarchive_cache.track table for tracks matching the given parameters.
    Returns a list of dicts with all needed metadata.
    """
    query = """\
        SELECT id, track_id, name, artist, album, stream_urls, artwork_url, data, last_updated
        FROM internetarchive_cache.track
    """
    filters = []
    params = {}
    if artist:
        filters.append("EXISTS (SELECT 1 FROM unnest(artist) a WHERE a ILIKE :artist)")
        params["artist"] = f"%{artist}%"
    if track:
        filters.append("name ILIKE :track")
        params["track"] = f"%{track}%"
    if album:
        filters.append("album ILIKE :album")
        params["album"] = f"%{album}%"

    if filters:
        query += " WHERE " + " AND ".join(filters)

    with db_conn.engine.connect() as conn:
        result = conn.execute(text(query), params)
        rows = result.mappings().all()

    tracks = []
    for row in rows:
       
        tracks.append({
            "id": row["id"],
            "track_id": row["track_id"],
            "name": row["name"],
            "artist": row["artist"],  
            "album": row["album"],
            "stream_urls": row["stream_urls"],  
            "artwork_url": row["artwork_url"],
            "data": row["data"], 
            "last_updated": row["last_updated"].isoformat() if row["last_updated"] else None,
        })
    return tracks