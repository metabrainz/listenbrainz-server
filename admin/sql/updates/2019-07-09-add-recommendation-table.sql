BEGIN;

CREATE SCHEMA recommendation;

CREATE TABLE recommendation.cf_recording (
  id                  SERIAL, -- PK
  user_id             INTEGER NOT NULL, --FK to "user".id
  msid                UUID NOT NULL,
  recommender_id      INTEGER, --FK to recommendation.recommender.id
  type                recording_type,
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recommendation.recommender (
  id                  SERIAL, --PK
  repository          TEXT NOT NULL,
  author_email        TEXT NOT NULL,
  name                TEXT NOT NULL,
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recommendation.cf_recording_recommender_join(
  last_used           TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  cf_recording_id     INTEGER, --FK to recommendation.cf_recording.id
  recommender_id      INTEGER --FK tol recommendation.recommender.id
);

--Create primary key
ALTER TABLE recommendation.cf_recording ADD CONSTRAINT rec_cf_recording_pkey PRIMARY KEY (id);
ALTER TABLE recommendation.recommender ADD CONSTRAINT rec_recommender_pkey PRIMARY KEY (id);

--Create foreign key
ALTER TABLE recommendation.cf_recording
    ADD CONSTRAINT cf_recording_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.cf_recording
    ADD CONSTRAINT cf_recording_recommender_id_foreign_key
    FOREIGN KEY (recommender_id)
    REFERENCES recommendation.recommender (id);

ALTER TABLE recommendation.cf_recording_recommender_join
    ADD CONSTRAINT cf_recording_recommender_join_recommender_id_foreign_key
    FOREIGN KEY (recommender_id)
    REFERENCES recommendation.recommender (id);

ALTER TABLE recommendation.cf_recording_recommender_join
    ADD CONSTRAINT cf_recording_recommender_join_cf_recording_id_foreign_key
    FOREIGN KEY (cf_recording_id)
    REFERENCES recommendation.cf_recording (id);

COMMIT;
