BEGIN;

CREATE TYPE user_relationship_enum AS ENUM('follow');

CREATE TABLE user_relationship (
    -- relationships go from 0 to 1
    -- for example, if relationship type is "follow", then user_0 follows user_1
    user_0              INTEGER NOT NULL, -- FK to "user".id
    user_1              INTEGER NOT NULL, -- FK to "user".id
    relationship_type   user_relationship_enum NOT NULL,
    created             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE user_relationship ADD CONSTRAINT user_relationship_pkey PRIMARY KEY (user_0, user_1, relationship_type);

ALTER TABLE user_relationship
    ADD CONSTRAINT user_relationship_user_0_foreign_key
    FOREIGN KEY (user_0)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE user_relationship
    ADD CONSTRAINT user_relationship_user_1_foreign_key
    FOREIGN KEY (user_1)
    REFERENCES "user" (id)
    ON DELETE CASCADE;


CREATE INDEX user_0_user_relationship_ndx ON user_relationship (user_0);
CREATE INDEX user_1_user_relationship_ndx ON user_relationship (user_1);

COMMIT;
