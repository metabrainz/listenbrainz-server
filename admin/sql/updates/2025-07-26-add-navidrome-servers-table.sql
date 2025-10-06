BEGIN;

DROP TABLE IF EXISTS navidrome_servers CASCADE;

CREATE TABLE navidrome_servers (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    host_url            TEXT NOT NULL UNIQUE,
    created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE navidrome_servers ADD CONSTRAINT navidrome_servers_id_pkey PRIMARY KEY (id);

CREATE INDEX host_url_ndx_navidrome_servers ON navidrome_servers (host_url);

COMMIT;
