BEGIN;

-- We added a column 'reason' after initially running this update script on the prod database,
-- so we first drop the table before recreating it.
DROP TABLE IF EXISTS reported_users;

CREATE TABLE reported_users (
    id                  SERIAL,
    reporter_user_id    INTEGER NOT NULL, -- FK to "user".id of the user who reported
    reported_user_id    INTEGER NOT NULL, -- FK to "user".id of the user who was reported
    reported_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason              TEXT
);

CREATE INDEX reporter_user_id_ndx_reported_users ON reported_users (reporter_user_id);
CREATE INDEX reported_user_id_ndx_reported_users ON reported_users (reported_user_id);
CREATE UNIQUE INDEX user_id_reports_ndx_reported_users ON reported_users (reporter_user_id, reported_user_id);

ALTER TABLE reported_users
    ADD CONSTRAINT  reporter_user_id_foreign_key
    FOREIGN KEY (reporter_user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE reported_users
    ADD CONSTRAINT  reported_user_id_foreign_key
    FOREIGN KEY (reported_user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;