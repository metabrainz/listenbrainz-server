BEGIN;

CREATE SCHEMA recommendation;

CREATE TYPE cf_recording_type AS ENUM('top_artist', 'similar_artist');

CREATE TABLE recommendation.cf_recording (
  id                  SERIAL, -- PK
  user_id             INTEGER NOT NULL, --FK to "user".id
  recording_msid      UUID NOT NULL,
  type                cf_recording_type NOT NULL,
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE recommendation.recommender (
  id                  SERIAL, --PK
  user_id             INTEGER NOT NULL, --FK to "user".id, denotes user who wrote software for this recommender.
  repository          TEXT NOT NULL,
  name                TEXT NOT NULL,
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE recommendation.recording_session (
  last_used           TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  recording_msid      UUID NOT NULL,
  session_id          INTEGER NOT NULL --FK to recommendation.recommender_session.id
);

CREATE TABLE recommendation.recommender_session (
  id                  SERIAL, --PK
  recommender_id      INTEGER NOT NULL, --FK to recommendation.recommender.id
  user_id             INTEGER NOT NULL, --FK to "user".id, user for whom the recommendations are generated.
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  data                JSONB
);

--Create primary key
ALTER TABLE recommendation.cf_recording ADD CONSTRAINT rec_cf_recording_pkey PRIMARY KEY (id);
ALTER TABLE recommendation.recommender ADD CONSTRAINT rec_recommender_pkey PRIMARY KEY (id);
ALTER TABLE recommendation.recommender_session ADD CONSTRAINT rec_recommender_session_pkey PRIMARY KEY (id);

--Create foreign key
ALTER TABLE recommendation.cf_recording
    ADD CONSTRAINT cf_recording_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.recommender
    ADD CONSTRAINT recommender_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.recording_session
    ADD CONSTRAINT recording_session_recommender_session_foreign_key
    FOREIGN KEY (session_id)
    REFERENCES recommendation.recommender_session (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.recommender_session
    ADD CONSTRAINT recommender_session_recommender_foreign_key
    FOREIGN KEY (recommender_id)
    REFERENCES recommendation.recommender (id)
    ON DELETE CASCADE;

COMMIT;
