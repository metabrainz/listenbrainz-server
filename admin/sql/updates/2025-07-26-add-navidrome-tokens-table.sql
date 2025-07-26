BEGIN;

CREATE TABLE navidrome_tokens (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    navidrome_server_id INTEGER NOT NULL REFERENCES navidrome_servers(id) ON DELETE CASCADE,
    username            TEXT NOT NULL,
    access_token        TEXT NOT NULL,
    created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX user_id_ndx_navidrome_tokens ON navidrome_tokens (user_id);
CREATE INDEX server_id_ndx_navidrome_tokens ON navidrome_tokens (navidrome_server_id);
CREATE UNIQUE INDEX unique_user_server_navidrome_tokens ON navidrome_tokens (user_id, navidrome_server_id);

COMMIT;
