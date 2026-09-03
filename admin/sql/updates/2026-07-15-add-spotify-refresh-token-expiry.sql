ALTER TABLE external_service_oauth
    ADD COLUMN refresh_token_expires TIMESTAMP WITH TIME ZONE,
    ADD COLUMN refresh_token_expiry_last_notified TIMESTAMP WITH TIME ZONE;
