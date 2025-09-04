BEGIN;

DROP TABLE IF EXISTS funkwhale_servers CASCADE;

CREATE TABLE funkwhale_servers (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    host_url            TEXT NOT NULL UNIQUE,
    client_id           TEXT NOT NULL,
    client_secret       TEXT NOT NULL,
    scopes              TEXT NOT NULL,
    created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE funkwhale_servers ADD CONSTRAINT funkwhale_servers_id_pkey PRIMARY KEY (id);

CREATE INDEX host_url_ndx_funkwhale_servers ON funkwhale_servers (host_url);

COMMIT;