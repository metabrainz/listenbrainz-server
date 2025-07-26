BEGIN;

CREATE TABLE funkwhale_tokens (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    funkwhale_server_id INTEGER NOT NULL REFERENCES funkwhale_servers(id) ON DELETE CASCADE,
    access_token        TEXT,
    refresh_token       TEXT,
    token_expiry        TIMESTAMP WITH TIME ZONE
);

CREATE INDEX user_id_ndx_funkwhale_tokens ON funkwhale_tokens (user_id);
CREATE INDEX server_id_ndx_funkwhale_tokens ON funkwhale_tokens (funkwhale_server_id);
CREATE UNIQUE INDEX unique_user_server_funkwhale_tokens ON funkwhale_tokens (user_id, funkwhale_server_id);

COMMIT; 