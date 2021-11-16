BEGIN;

CREATE TABLE statistics.year_in_music (
    user_id     INTEGER NOT NULL, -- PK and FK to "user".id
    data        JSONB
);

ALTER TABLE statistics.year_in_music ADD CONSTRAINT stats_year_in_music_pkey PRIMARY KEY (user_id);

ALTER TABLE statistics.year_in_music
    ADD CONSTRAINT user_stats_year_in_music_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
