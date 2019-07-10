BEGIN;

CREATE SCHEMA recommendations;

CREATE TABLE recommendations.recording (
  id                  SERIAL, --PK
  user_id             INTEGER NOT NULL, -- FK to "user".id
  msid                UUID NOT NULL,
  last_used           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  created             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

--Create primary key
ALTER TABLE recommendation ADD CONSTRAINT rec_pkey PRIMARY KEY (id);

--Create foreign key
ALTER TABLE recommendation ADD CONSTRAINT user_rec_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);

COMMIT;
