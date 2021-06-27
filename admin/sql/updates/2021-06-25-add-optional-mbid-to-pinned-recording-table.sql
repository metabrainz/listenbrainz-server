BEGIN;

-- this table is currently empty, we can drop it and recreate it with the new changes.

DROP TABLE IF EXISTS pinned_recording;

-- Changes: added a required recording_msid column,
-- recording_mbid column is now optional

CREATE TABLE pinned_recording(
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    recording_msid          UUID NOT NULL,
    recording_mbid          UUID,
    blurb_content           TEXT,
    pinned_until            TIMESTAMP WITH TIME ZONE NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE pinned_recording ADD CONSTRAINT pinned_recording_pkey PRIMARY KEY (id);

ALTER TABLE pinned_recording
    ADD CONSTRAINT pinned_recording_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX user_id_ndx_pinned_recording ON pinned_recording (user_id);

COMMIT;