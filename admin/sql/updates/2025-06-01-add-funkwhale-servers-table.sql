BEGIN;

DROP TABLE IF EXISTS funkwhale_servers CASCADE;

CREATE TABLE funkwhale_servers (
    id          SERIAL PRIMARY KEY,
    host_url    TEXT NOT NULL UNIQUE,
    client_id   TEXT,
    client_secret TEXT,
    scopes      TEXT,
    created     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX host_url_ndx_funkwhale_servers ON funkwhale_servers (host_url);

COMMIT;