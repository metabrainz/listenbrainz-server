from sqlalchemy import text
import contextlib

SPOTIFY_EXPORT_PREFERENCE = "export_to_spotify"

@contextlib.contextmanager
def intercept_apple_music_errors():
    try:
        import troi.http_request
    except ImportError:
        yield
        return

    original_http_fetch = troi.http_request.http_fetch

    def patched_http_fetch(url, method, headers=None, params=None, **kwargs):
        resp = original_http_fetch(url, method, headers=headers, params=params, **kwargs)
        if "api.music.apple.com" in url and resp.status_code >= 400:
            try:
                err = resp.json()
                if "errors" in err and isinstance(err["errors"], list) and len(err["errors"]) > 0:
                    details = err["errors"][0].get("detail", err["errors"][0].get("title", f"Unknown error (HTTP {resp.status_code})"))
                    if resp.status_code in (401, 403):
                        raise Exception(f"Apple Music authentication failed: {details}. Please disconnect and reconnect your Apple Music account.")
                    raise Exception(f"Apple Music API error: {details}")
            except Exception:
                pass
            if resp.status_code in (401, 403):
                raise Exception("Apple Music authentication failed. Please disconnect and reconnect your Apple Music account.")
            raise Exception(f"Apple Music API error: HTTP {resp.status_code}")
        return resp

    troi.http_request.http_fetch = patched_http_fetch
    try:
        yield
    finally:
        troi.http_request.http_fetch = original_http_fetch


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
