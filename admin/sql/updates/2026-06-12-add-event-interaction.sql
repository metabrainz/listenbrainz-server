BEGIN;

CREATE TYPE event_interaction_enum AS ENUM('watch');

CREATE TABLE event_interaction (
    user_id              INTEGER NOT NULL, -- FK to "user".id
    event_mbid           UUID NOT NULL,
    interaction_type     event_interaction_enum NOT NULL,
    created              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE event_interaction
    ADD CONSTRAINT event_interaction_pkey
    PRIMARY KEY (user_id, event_mbid, interaction_type);

ALTER TABLE event_interaction
    ADD CONSTRAINT event_interaction_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX user_id_event_interaction_ndx ON event_interaction (user_id);
CREATE INDEX event_mbid_event_interaction_ndx ON event_interaction (event_mbid);

COMMIT;
