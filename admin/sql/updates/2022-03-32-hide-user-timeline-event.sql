BEGIN;

CREATE TYPE hide_user_timeline_event_type_enum AS ENUM('recording_recommendation', 'recording_pin');

CREATE TABLE hide_user_timeline_event (
    id           SERIAL,  --PK
    user_id      INTEGER, --FK to "user"
    event_type   hide_user_timeline_event_type_enum,
    event_id     INTEGER,
    created      TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

ALTER TABLE hide_user_timeline_event
    ADD CONSTRAINT hide_user_timeline_event_pkey
    PRIMARY KEY (id);

ALTER TABLE hide_user_timeline_event
    ADD CONSTRAINT hide_user_timeline_event_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
