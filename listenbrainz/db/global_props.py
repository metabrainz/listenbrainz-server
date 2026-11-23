from typing import Any, Dict

import sqlalchemy


def get_global_props_data(db_conn, user_id: int) -> Dict[str, Any]:
    """ Fetch everything the props of an HTML page need about the logged-in user in one query.

    Args:
        db_conn: database connection
        user_id: the ListenBrainz row ID of the user

    Returns:
        a dict with
         - user_id
         - oauth_tokens: service name -> {access_token, refresh_token, scopes} for every connected
           OAuth service
         - funkwhale: the user's first Funkwhale connection with its server, or None
         - navidrome: the user's Navidrome connection with its server, or None
         - user_setting: {brainzplayer, flair} if the user has a user_setting row, or None
         - spotify_import_error: the error of the user's Spotify importer, or None
    """
    row = db_conn.execute(sqlalchemy.text("""
        SELECT (SELECT jsonb_object_agg(service, jsonb_build_object(
                           'access_token', access_token, 'refresh_token', refresh_token, 'scopes', scopes))
                  FROM external_service_oauth
                 WHERE user_id = :user_id) AS oauth_tokens
             , (SELECT error
                  FROM listens_importer
                 WHERE user_id = :user_id
                   AND service = 'spotify') AS spotify_import_error
             , fw.access_token AS funkwhale_access_token
             , fw.refresh_token AS funkwhale_refresh_token
             , fw.token_expiry AS funkwhale_token_expiry
             , fw.server_id AS funkwhale_server_id
             , fw.host_url AS funkwhale_host_url
             , fw.client_id AS funkwhale_client_id
             , fw.client_secret AS funkwhale_client_secret
             , nd.encrypted_password AS navidrome_encrypted_password
             , nd.username AS navidrome_username
             , nd.host_url AS navidrome_host_url
             , us.user_id IS NOT NULL AS has_user_setting
             , us.brainzplayer
             , us.flair
          FROM (SELECT 1) AS one
     LEFT JOIN (SELECT t.access_token, t.refresh_token, t.token_expiry, s.id AS server_id, s.host_url
                     , s.client_id, s.client_secret
                  FROM funkwhale_tokens t
                  JOIN funkwhale_servers s
                    ON t.funkwhale_server_id = s.id
                 WHERE t.user_id = :user_id
              ORDER BY t.id
                 LIMIT 1) AS fw
            ON TRUE
     LEFT JOIN (SELECT t.encrypted_password, t.username, s.host_url
                  FROM navidrome_tokens t
                  JOIN navidrome_servers s
                    ON t.navidrome_server_id = s.id
                 WHERE t.user_id = :user_id
                 LIMIT 1) AS nd
            ON TRUE
     LEFT JOIN user_setting us
            ON us.user_id = :user_id
    """), {"user_id": user_id}).mappings().first()

    funkwhale = None
    if row["funkwhale_server_id"] is not None:
        funkwhale = {
            "access_token": row["funkwhale_access_token"],
            "refresh_token": row["funkwhale_refresh_token"],
            "token_expiry": row["funkwhale_token_expiry"],
            "server_id": row["funkwhale_server_id"],
            "host_url": row["funkwhale_host_url"],
            "client_id": row["funkwhale_client_id"],
            "client_secret": row["funkwhale_client_secret"],
        }

    navidrome = None
    if row["navidrome_host_url"] is not None:
        navidrome = {
            "encrypted_password": row["navidrome_encrypted_password"],
            "username": row["navidrome_username"],
            "host_url": row["navidrome_host_url"],
        }

    user_setting = None
    if row["has_user_setting"]:
        user_setting = {"brainzplayer": row["brainzplayer"], "flair": row["flair"]}

    return {
        "user_id": user_id,
        "oauth_tokens": row["oauth_tokens"] or {},
        "funkwhale": funkwhale,
        "navidrome": navidrome,
        "user_setting": user_setting,
        "spotify_import_error": row["spotify_import_error"],
    }
