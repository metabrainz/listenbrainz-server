BEGIN;

ALTER TABLE statistics.year_in_music ADD COLUMN year SMALLINT;

-- update existing year in music rows to 2021
UPDATE statistics.year_in_music SET year = 2021;

ALTER TABLE statistics.year_in_music ALTER COLUMN year SET NOT NULL;

COMMIT;
