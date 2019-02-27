BEGIN;

CREATE TABLE follow_list (
  id                SERIAL, -- PK
  name              TEXT NOT NULL,
  creator           INTEGER NOT NULL, -- FK to "user".id
  private           BOOLEAN NOT NULL DEFAULT FALSE,
  created           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  last_listened     TIMESTAMP WITH TIME ZONE
);

ALTER TABLE follow_list ADD CONSTRAINT follow_list_name_creator_key UNIQUE (name, creator);

CREATE TABLE follow_list_member (
  list_id      INTEGER NOT NULL,
  user_id      INTEGER NOT NULL,
  added        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE follow_list ADD CONSTRAINT follow_list_pkey PRIMARY KEY (id);
ALTER TABLE follow_list_member ADD CONSTRAINT follow_list_member_pkey PRIMARY KEY (list_id, user_id);

ALTER TABLE follow_list
    ADD CONSTRAINT follow_list_user_id_foreign_key
    FOREIGN KEY (creator)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE follow_list_member
    ADD CONSTRAINT follow_list_member_list_id_foreign_key
    FOREIGN KEY (list_id)
    REFERENCES follow_list (id)
    ON DELETE CASCADE;

ALTER TABLE follow_list_member
    ADD CONSTRAINT follow_list_member_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX creator_ndx_follow_list ON follow_list (creator);
CREATE INDEX last_listened_ndx_follow_list ON follow_list (last_listened DESC NULLS LAST);

COMMIT;
