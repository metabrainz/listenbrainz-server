BEGIN;

UPDATE statistics.year_in_music
SET data = data - 'yim_artist_map'
WHERE year = 2022 AND data ? 'yim_artist_map';

COMMIT;
