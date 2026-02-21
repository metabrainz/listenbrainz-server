from sqlalchemy import text

SPOTIFY_EXPORT_PREFERENCE = "export_to_spotify"


def get_existing_playlist_urls(ts_conn, user_ids: list[int], playlist_slug):
    """ Retrieve urls of the existing spotify playlists of daily jams users """
    query = """
        SELECT DISTINCT ON (created_for_id)
               created_for_id
             , additional_metadata->'external_urls'->>'spotify' AS spotify_url
          FROM playlist.playlist
         WHERE additional_metadata->'algorithm_metadata'->>'source_patch' = :playlist_slug
           AND created_for_id = ANY(:user_ids)
      ORDER BY created_for_id, created DESC
    """
    results = ts_conn.execute(text(query), {"user_ids": user_ids, "playlist_slug": playlist_slug})
    return {r.created_for_id: r.spotify_url for r in results}
