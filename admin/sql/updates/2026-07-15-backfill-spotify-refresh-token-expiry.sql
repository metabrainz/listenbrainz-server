UPDATE external_service_oauth
   SET refresh_token_expires = '2026-07-20 00:00:00+00'::TIMESTAMP WITH TIME ZONE
 WHERE service = 'spotify'
   AND refresh_token IS NOT NULL
   AND refresh_token != ''
   AND refresh_token_expires IS NULL;
