-- For empty installations only. For existing data, copy the statistics schema from Timescale
-- with pg_dump/pg_restore instead.
BEGIN;
CREATE SCHEMA statistics; -- this schema is used to store the YIM tables, tables are created dynamically in listenbrainz/db/year_in_music.py

CREATE TABLE statistics.year_in_music_cover (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    user_id             INTEGER NOT NULL,
    year                SMALLINT NOT NULL,
    caa_id              BIGINT,
    caa_release_mbid    UUID
);

ALTER TABLE statistics.year_in_music_cover ADD CONSTRAINT year_in_music_cover_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX year_in_music_cover_user_id_idx ON statistics.year_in_music_cover (user_id, year);
COMMIT;
