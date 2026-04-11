BEGIN;

CREATE SCHEMA youtube_cache;

CREATE TABLE youtube_cache.video (
    id            INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    video_id      TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    channel_name  TEXT NOT NULL,
    last_updated  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX youtube_cache_video_video_id_idx ON youtube_cache.video (video_id);

COMMIT;
