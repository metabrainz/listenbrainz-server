BEGIN;

CREATE TABLE follow_list (
  id                SERIAL, -- PK
  name              TEXT NOT NULL,
  creator           INTEGER NOT NULL, -- FK to "user".id
  private           BOOLEAN NOT NULL DEFAULT FALSE,
  members           INTEGER ARRAY NOT NULL DEFAULT ARRAY[]::INTEGER[],
  created           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  last_saved        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE follow_list ADD CONSTRAINT follow_list_name_creator_key UNIQUE (name, creator);
ALTER TABLE follow_list ADD CONSTRAINT follow_list_pkey PRIMARY KEY (id);

ALTER TABLE follow_list
    ADD CONSTRAINT follow_list_user_id_foreign_key
    FOREIGN KEY (creator)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX creator_ndx_follow_list ON follow_list (creator);
CREATE INDEX last_saved_ndx_follow_list ON follow_list (last_saved DESC);

COMMIT;
