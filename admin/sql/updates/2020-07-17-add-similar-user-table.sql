BEGIN;

CREATE TABLE recommendation.similar_user (
  user_id         INTEGER NOT NULL, -- FK to "user".id
  similar_users   JSONB,
  last_updated    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE recommendation.similar_user
    ADD CONSTRAINT similar_user_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE UNIQUE INDEX user_id_ndx_similar_user ON recommendation.similar_user (user_id);

COMMIT;
