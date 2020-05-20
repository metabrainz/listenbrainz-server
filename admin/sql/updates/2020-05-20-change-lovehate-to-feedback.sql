BEGIN;

-- Drop old table
DROP TABLE IF EXISTS recording_lovehate CASCADE;

-- Create new table
CREATE TABLE recording_feedback (
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    recording_msid          UUID NOT NULL,
    score                   SMALLINT NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create primary key
ALTER TABLE recording_feedback ADD CONSTRAINT recording_feedback_pkey PRIMARY KEY (id);

-- Create foreign key
ALTER TABLE recording_feedback ADD CONSTRAINT recording_feedback_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE;

-- Create unique index
CREATE UNIQUE INDEX user_id_rec_msid_ndx_feedback ON recording_feedback (user_id, recording_msid);

COMMIT;
