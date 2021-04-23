BEGIN;
truncate table external_service_oauth cascade;
WITH migration AS
    (
        INSERT INTO external_service_oauth
        (
         user_id,
         service,
         access_token,
         refresh_token,
         token_expires,
         last_updated,
         scopes
        )
        SELECT
            user_id,
            'spotify',
            user_token,
            refresh_token,
            token_expires,
            last_updated,
            string_to_array(permission, ' ')
        FROM spotify_auth
        RETURNING external_service_oauth.id as external_service_oauth_id, user_id
    )
INSERT INTO listens_importer
    (
     external_service_oauth_id,
     user_id,
     service,
     latest_listened_at,
     last_updated,
     error_message
    )
SELECT
    external_service_oauth_id,
    spotify_auth.user_id,
    'spotify',
    latest_listened_at,
    last_updated,
    error_message
FROM spotify_auth
JOIN migration ON spotify_auth.user_id = migration.user_id
WHERE record_listens = 't';

COMMIT;
