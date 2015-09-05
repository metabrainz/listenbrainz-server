BEGIN;

CREATE TABLE highlevel (
    id          INTEGER, -- FK to lowlevel.id
    mbid        UUID NOT NULL,
    build_sha1  TEXT NOT NULL,
    data        INTEGER NOT NULL, -- FK to highlevel_json.data
    submitted   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE highlevel_json (
    id           SERIAL,
    data         JSON NOT NULL,
    data_sha256  CHAR(64) NOT NULL
);

ALTER TABLE highlevel ADD CONSTRAINT highlevel_pkey PRIMARY KEY (id);
ALTER TABLE highlevel_json ADD CONSTRAINT highlevel_json_pkey PRIMARY KEY (id);

ALTER TABLE highlevel ADD CONSTRAINT highlevel_fk_lowlevel
    FOREIGN KEY (id) REFERENCES lowlevel(id);
ALTER TABLE highlevel ADD CONSTRAINT highlevel_fk_highlevel_json
    FOREIGN KEY (data) REFERENCES highlevel_json(id);

CREATE INDEX mbid_ndx_highlevel ON highlevel (mbid);
CREATE INDEX build_sha1_ndx_highlevel ON lowlevel (build_sha1);

COMMIT;
