BEGIN;

CREATE TABLE statistics.legacy_year_in_music_2021 (LIKE statistics.year_in_music_2021 INCLUDING ALL);
INSERT INTO statistics.legacy_year_in_music_2021 SELECT * FROM statistics.year_in_music_2021;

CREATE TABLE statistics.legacy_year_in_music_2022 (LIKE statistics.year_in_music_2022 INCLUDING ALL);
INSERT INTO statistics.legacy_year_in_music_2022 SELECT * FROM statistics.year_in_music_2022;

CREATE TABLE statistics.legacy_year_in_music_2023 (LIKE statistics.year_in_music_2023 INCLUDING ALL);
INSERT INTO statistics.legacy_year_in_music_2023 SELECT * FROM statistics.year_in_music_2023;

CREATE TABLE statistics.legacy_year_in_music_2024 (LIKE statistics.year_in_music_2024 INCLUDING ALL);
INSERT INTO statistics.legacy_year_in_music_2024 SELECT * FROM statistics.year_in_music_2024;

COMMIT;
