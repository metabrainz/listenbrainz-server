BEGIN;

CREATE INDEX mbid_ndx_lowlevel ON lowlevel (mbid);
CREATE INDEX build_sha1_ndx_lowlevel ON lowlevel (build_sha1);
CREATE UNIQUE INDEX data_sha256_ndx_lowlevel ON lowlevel (data_sha256);

CREATE INDEX mbid_ndx_highlevel ON highlevel (mbid);
CREATE INDEX build_sha1_ndx_highlevel ON lowlevel (build_sha1);

COMMIT;
