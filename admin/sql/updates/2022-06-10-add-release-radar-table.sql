BEGIN;

CREATE TABLE recommendation.release_radar (
  user_id         INTEGER NOT NULL, -- FK to "user".id
  data            JSONB,
  last_updated    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE recommendation.release_radar ADD CONSTRAINT rec_release_radar_pkey PRIMARY KEY (user_id);

ALTER TABLE recommendation.release_radar
    ADD CONSTRAINT release_radar_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE UNIQUE INDEX user_id_ndx_release_radar ON recommendation.release_radar (user_id);

COMMIT;
