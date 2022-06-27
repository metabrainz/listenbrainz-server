BEGIN;

CREATE TABLE CREATE TABLE user_setting(
    id                     SERIAL, --PK
    user_id                INTEGER NOT NULL, --FK to "user".id
    timezone_name          TEXT NOT NULL CHECK (now() AT TIME ZONE timezone_name IS NOT NULL)   
);

ALTER TABLE user_setting ADD CONSTRAINT setting_user_id_unique UNIQUE (user_id);

ALTER TABLE user_setting
    ADD CONSTRAINT user_setting_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE user_setting ADD CONSTRAINT user_setting_pkey PRIMARY KEY (id);

COMMIT;