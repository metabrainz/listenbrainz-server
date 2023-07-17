CREATE TYPE tag_source_type_enum AS ENUM ('recording', 'artist', 'release-group');

BEGIN;

CREATE TABLE tags.tags (
    tag                     TEXT NOT NULL,
    recording_mbid          UUID NOT NULL,
    tag_count               INTEGER NOT NULL,
    percent                 DOUBLE PRECISION NOT NULL,
    source                  tag_source_type_enum NOT NULL
);

CREATE INDEX tags_tag_percent_idx ON tags.tags (tag, percent) INCLUDE (source, recording_mbid, tag_count);

commit;
