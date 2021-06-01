BEGIN;

CREATE TABLE pinned_track(
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    recording_mbid          UUID NOT NULL,
    blurb_content           VARCHAR,
    currently_pinned        BOOLEAN NOT NULL DEFAULT TRUE,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE pinned_track ADD CONSTRAINT pinned_track_pkey PRIMARY KEY (id);

ALTER TABLE pinned_track
    ADD CONSTRAINT pinned_track_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE UNIQUE INDEX user_id_rec_mbid_ndx_pinned_track ON pinned_track (user_id, recording_mbid);

COMMIT;