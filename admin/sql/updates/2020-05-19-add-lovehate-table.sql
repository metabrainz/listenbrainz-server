BEGIN;

-- Create new table
CREATE TABLE recording_lovehate (
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    recording_msid          UUID NOT NULL,
    score                   SMALLINT NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create primary key
ALTER TABLE recording_lovehate ADD CONSTRAINT recording_lovehate_pkey PRIMARY KEY (id);

-- Create foreign key
ALTER TABLE recording_lovehate ADD CONSTRAINT recording_lovehate_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE;

COMMIT;
