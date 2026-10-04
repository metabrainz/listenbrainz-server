BEGIN;

CREATE TYPE user_artist_relationship_enum AS ENUM('follow');

CREATE TABLE user_artist_relationship (
    user_id              INTEGER NOT NULL, -- FK to "user".id
    artist_mbid          UUID NOT NULL,
    relationship_type    user_artist_relationship_enum NOT NULL,
    created              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE user_artist_relationship
    ADD CONSTRAINT user_artist_relationship_pkey
    PRIMARY KEY (user_id, artist_mbid, relationship_type);

ALTER TABLE user_artist_relationship
    ADD CONSTRAINT user_artist_relationship_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

-- No index on user_id: it is the leading column of the composite primary key
-- above, so the PK index already serves user_id lookups and the cascading delete.
CREATE INDEX artist_mbid_user_artist_relationship_ndx ON user_artist_relationship (artist_mbid);

COMMIT;
