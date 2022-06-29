BEGIN;

CREATE TABLE user_setting(
    id                     SERIAL, --PK
    user_id                INTEGER NOT NULL, --FK to "user".id
    timezone_name          TEXT   
);

ALTER TABLE user_setting
    ADD CONSTRAINT user_setting_timezone_name_check
    CHECK ( timezone_name IS NULL OR now() AT TIME ZONE timezone_name IS NOT NULL );

ALTER TABLE user_setting
    ADD CONSTRAINT user_setting_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE user_setting ADD CONSTRAINT user_setting_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX user_id_ndx_user_setting ON user_setting (user_id);

COMMIT;