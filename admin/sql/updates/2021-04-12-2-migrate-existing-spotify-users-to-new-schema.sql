BEGIN;
INSERT INTO external_service_oauth
    (
     user_id,
     service,
     access_token,
     refresh_token,
     token_expires,
     last_updated,
     record_listens,
     service_details
    )
SELECT user_id,
       'spotify' as service,
       user_token as access_token,
       refresh_token,
       token_expires,
       last_updated,
       record_listens,
       jsonb_build_object(
           'latest_listened_at', latest_listened_at,
           'error_message', error_message,
           'permission', permission
           )
FROM spotify_auth;
COMMIT;
