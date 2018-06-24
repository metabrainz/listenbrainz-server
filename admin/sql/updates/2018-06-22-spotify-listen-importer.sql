BEGIN;

CREATE TABLE spotify (
  user_id         INTEGER NOT NULL, -- FK to user.id
  user_token      VARCHAR NOT NULL,
  token_expires   TIMESTAMP WITH TIME ZONE,
  refresh_token   VARCHAR NOT NULL,
  last_updated    TIMESTAMP WITH TIME ZONE,
  active          BOOLEAN DEFAULT TRUE,
  update_error    VARCHAR
);

ALTER TABLE spotify ADD CONSTRAINT spotify_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);

ALTER TABLE spotify ADD CONSTRAINT spotify_pkey PRIMARY KEY (user_id);

COMMIT;
