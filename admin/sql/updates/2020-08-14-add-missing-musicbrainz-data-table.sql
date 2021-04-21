BEGIN;

CREATE TYPE mb_missing_data_source AS ENUM('cf', 'artist_map');

CREATE TABLE missing_musicbrainz_data (
    id              SERIAL, -- PK
    user_id         INTEGER NOT NULL, --FK to "user".id
    data            JSONB NOT NULL,
    source          mb_missing_data_source NOT NULL,
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

ALTER TABLE missing_musicbrainz_data ADD CONSTRAINT user_id_unique UNIQUE (user_id);

--Create primary key
ALTER TABLE missing_musicbrainz_data ADD CONSTRAINT missing_mb_data_pkey PRIMARY KEY (id);

--Create foreign key
ALTER TABLE missing_musicbrainz_data
    ADD CONSTRAINT missing_mb_data_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
