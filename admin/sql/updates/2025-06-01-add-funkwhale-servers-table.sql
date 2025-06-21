BEGIN;

CREATE TABLE funkwhale_servers (
    user_id                 INTEGER NOT NULL,
    host_url                TEXT NOT NULL,
    client_id               TEXT,
    client_secret           TEXT,
    access_token            TEXT,
    refresh_token           TEXT,
    token_expiry            TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, host_url)
);

CREATE INDEX user_id_ndx_funkwhale_servers ON funkwhale_servers (user_id);
CREATE INDEX host_url_ndx_funkwhale_servers ON funkwhale_servers (host_url);

COMMIT;