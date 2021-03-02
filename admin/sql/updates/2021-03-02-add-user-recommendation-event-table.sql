BEGIN;

CREATE TYPE user_timeline_event_type_enum AS ENUM('recording');

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

COMMIT;
