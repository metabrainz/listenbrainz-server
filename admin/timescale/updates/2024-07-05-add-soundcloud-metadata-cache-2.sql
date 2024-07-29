BEGIN;


ALTER TABLE soundcloud_cache.track ADD COLUMN release_year INTEGER;
ALTER TABLE soundcloud_cache.track ADD COLUMN release_month INTEGER;
ALTER TABLE soundcloud_cache.track ADD COLUMN release_day INTEGER;

UPDATE soundcloud_cache.track
   SET release_year = (data->>'release_year')::int
     , release_month = (data->>'release_month')::int
     , release_day = (data->>'release_day')::int;

COMMIT;
