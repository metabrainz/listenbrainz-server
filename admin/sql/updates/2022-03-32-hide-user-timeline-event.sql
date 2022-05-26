BEGIN;

CREATE TYPE hide_user_timeline_event_type_enum AS ENUM('recording_recommendation', 'recording_pin');

CREATE TABLE hide_user_timeline_event (
    id           SERIAL NOT NULL,  --PK
    user_id      INTEGER NOT NULL, --FK to "user"
    event_type   hide_user_timeline_event_type_enum NOT NULL,
    event_id     INTEGER NOT NULL, --Row ID of recommendation or pin
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

CREATE UNIQUE INDEX user_id_event_type_event_id_ndx_hide_user_timeline_event ON hide_user_timeline_event (user_id, event_type, event_id);

COMMIT;
