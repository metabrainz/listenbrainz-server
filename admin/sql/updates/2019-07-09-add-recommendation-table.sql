BEGIN;

CREATE SCHEMA recommendations;

CREATE TABLE recommendations.top_artist (
  id                  SERIAL, --PK
  user_id             INTEGER NOT NULL, -- FK to "user".id
  recording_msid      UUID NOT NULL,
  last_used           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  created             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE recommendations.similar_artist (
  id                  SERIAL, --PK
  user_id             INTEGER NOT NULL, -- FK to "user".id
  recording_msid      UUID NOT NULL,
  last_used           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  created             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

--Create primary key
ALTER TABLE recommendations.top_artist ADD CONSTRAINT top_artist_pkey PRIMARY KEY (id);
ALTER TABLE recommendations.similar_artist ADD CONSTRAINT similar_artist_pkey PRIMARY KEY (id);

--Create foreign key
ALTER TABLE recommendations.top_artist ADD CONSTRAINT user_top_artist_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);
ALTER TABLE recommendations.similar_artist ADD CONSTRAINT user_similar_artist_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);

COMMIT;
