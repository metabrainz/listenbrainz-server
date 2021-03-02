BEGIN;

CREATE TYPE user_recommendation_event_type_enum AS ENUM('recording');

CREATE TABLE recommendation.user_recommendation_event (
  id                    SERIAL, -- PK
  user_id               INTEGER, -- FK to "user"
  recommendation_type   user_recommendation_event_type_enum,
  metadata              JSONB,
  created               TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);


ALTER TABLE recommendation.user_recommendation_event ADD CONSTRAINT rec_user_recommendation_event_pkey PRIMARY KEY (id);

ALTER TABLE recommendation.user_recommendation_event
    ADD CONSTRAINT user_recommendation_event_user_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
