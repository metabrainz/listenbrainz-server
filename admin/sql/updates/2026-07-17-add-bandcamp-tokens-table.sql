BEGIN;

DROP TABLE IF EXISTS bandcamp_tokens;

CREATE TABLE bandcamp_tokens (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id             INTEGER NOT NULL,
    username            TEXT NOT NULL,
    encrypted_password  TEXT NOT NULL,
    created             TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE bandcamp_tokens ADD CONSTRAINT bandcamp_tokens_id_pkey PRIMARY KEY (id);

ALTER TABLE bandcamp_tokens
    ADD CONSTRAINT bandcamp_tokens_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE UNIQUE INDEX user_id_ndx_bandcamp_tokens ON bandcamp_tokens (user_id);

COMMIT;
