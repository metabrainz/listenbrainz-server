BEGIN;

CREATE TABLE cover_art (
    id                      SERIAL, -- PK
    release_mbid            UUID NOT NULL,
    image_url               VARCHAR NOT NULL,
    source                  VARCHAR NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE cover_art ADD CONSTRAINT cover_art_pkey PRIMARY KEY (id); 

CREATE UNIQUE INDEX rel_mbid_src_ndx_cover_art ON cover_art (release_mbid, source);

COMMIT;