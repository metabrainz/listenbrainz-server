BEGIN;

DROP TABLE IF EXISTS funkwhale_tokens;

CREATE TABLE funkwhale_tokens (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id             INTEGER NOT NULL,
    funkwhale_server_id INTEGER NOT NULL,
    access_token        TEXT NOT NULL,
    refresh_token       TEXT NOT NULL,
    token_expiry        TIMESTAMP WITH TIME ZONE NOT NULL
);

ALTER TABLE funkwhale_tokens ADD CONSTRAINT funkwhale_tokens_id_pkey PRIMARY KEY (id);

ALTER TABLE funkwhale_tokens
    ADD CONSTRAINT funkwhale_tokens_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE funkwhale_tokens
    ADD CONSTRAINT funkwhale_tokens_server_id_foreign_key
    FOREIGN KEY (funkwhale_server_id)
    REFERENCES funkwhale_servers (id)
    ON DELETE CASCADE;

CREATE INDEX user_id_ndx_funkwhale_tokens ON funkwhale_tokens (user_id);
CREATE INDEX server_id_ndx_funkwhale_tokens ON funkwhale_tokens (funkwhale_server_id);
CREATE UNIQUE INDEX unique_user_server_funkwhale_tokens ON funkwhale_tokens (user_id, funkwhale_server_id);

COMMIT; 