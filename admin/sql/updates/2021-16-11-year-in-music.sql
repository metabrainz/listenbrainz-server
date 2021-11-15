BEGIN;

CREATE TABLE statistics.year_in_music (
    id                              SERIAL,
    user_id                         INTEGER NOT NULL, -- FK to "user".id
    new_releases_of_top_artists     JSONB
);

ALTER TABLE statistics.year_in_music ADD CONSTRAINT stats_year_in_music_pkey PRIMARY KEY (id);

ALTER TABLE statistics.year_in_music
    ADD CONSTRAINT user_stats_year_in_music_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX user_id_ndx_year_in_music_new ON statistics.year_in_music (user_id);

COMMIT;
