BEGIN;

DROP TABLE IF EXISTS navidrome_tokens;

CREATE TABLE navidrome_tokens (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id             INTEGER NOT NULL,
    navidrome_server_id INTEGER NOT NULL,
    username            TEXT NOT NULL,
    encrypted_password  TEXT NOT NULL,
    created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE navidrome_tokens ADD CONSTRAINT navidrome_tokens_id_pkey PRIMARY KEY (id);

ALTER TABLE navidrome_tokens
    ADD CONSTRAINT navidrome_tokens_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE navidrome_tokens
    ADD CONSTRAINT navidrome_tokens_server_id_foreign_key
    FOREIGN KEY (navidrome_server_id)
    REFERENCES navidrome_servers (id)
    ON DELETE CASCADE;

CREATE INDEX user_id_ndx_navidrome_tokens ON navidrome_tokens (user_id);
CREATE INDEX server_id_ndx_navidrome_tokens ON navidrome_tokens (navidrome_server_id);
CREATE UNIQUE INDEX unique_user_server_navidrome_tokens ON navidrome_tokens (user_id, navidrome_server_id);

COMMIT;
