CREATE SCHEMA tags;
CREATE TYPE lb_tag_radio_source_type_enum AS ENUM ('recording', 'artist', 'release-group');

BEGIN;

CREATE TABLE tags.lb_tag_radio (
    tag                     TEXT NOT NULL,
    recording_mbid          UUID NOT NULL,
    tag_count               INTEGER NOT NULL,
    percent                 DOUBLE PRECISION NOT NULL,
    source                  lb_tag_radio_source_type_enum NOT NULL
);

CREATE INDEX tags_lb_tag_radio_percent_idx ON tags.lb_tag_radio (tag, percent) INCLUDE (source, recording_mbid, tag_count);

commit;
