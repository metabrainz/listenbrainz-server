BEGIN;

CREATE TABLE navidrome_servers (
    id          SERIAL PRIMARY KEY,
    host_url    TEXT NOT NULL UNIQUE,
    created     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX host_url_ndx_navidrome_servers ON navidrome_servers (host_url);

COMMIT;
