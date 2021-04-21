BEGIN;

CREATE TYPE user_timeline_event_type_enum AS ENUM('recording_recommendation');

CREATE TABLE user_timeline_event (
  id                    SERIAL, -- PK
  user_id               INTEGER, -- FK to "user"
  event_type            user_timeline_event_type_enum,
  metadata              JSONB,
  created               TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);


ALTER TABLE user_timeline_event ADD CONSTRAINT user_timeline_event_pkey PRIMARY KEY (id);

ALTER TABLE user_timeline_event
    ADD CONSTRAINT user_timeline_event_user_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX user_id_ndx_user_timeline_event ON user_timeline_event (user_id);
CREATE INDEX event_type_ndx_user_timeline_event ON user_timeline_event (event_type);
CREATE INDEX user_id_event_type_ndx_user_timeline_event ON user_timeline_event (user_id, event_type);

COMMIT;
