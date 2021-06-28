BEGIN;
UPDATE "user"
    SET login_id = uuid_generate_v4()::text;
COMMIT;
