BEGIN;

CREATE TABLE missing_releases_musicbrainz (
    id              SERIAL, -- PK
    user_id         INTEGER NOT NULL, --FK to "user".id
    data            JSONB NOT NULL,
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

ALTER TABLE missing_releases_musicbrainz ADD CONSTRAINT user_id_unique UNIQUE (user_id);

--Create primary key
ALTER TABLE missing_releases_musicbrainz ADD CONSTRAINT missing_releases_mb_pkey PRIMARY KEY (id);

--Create foreign key
ALTER TABLE missing_releases_musicbrainz
    ADD CONSTRAINT missing_releases_mb_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
