CREATE SCHEMA musicbrainz;
CREATE SCHEMA cover_art_archive;
SET search_path TO musicbrainz;

CREATE TABLE artist (id int, gid uuid, name text, area int);
CREATE TABLE iso_3166_1 (area int, code text);
CREATE TABLE area_containment (parent int, descendant int);
CREATE TABLE artist_credit (id int, name text);
CREATE TABLE artist_credit_name (artist_credit int, artist int, position smallint, name text, join_phrase text);
CREATE TABLE recording (id int, gid uuid, length int, artist_credit int);
CREATE TABLE recording_gid_redirect (gid uuid, new_id int);
CREATE TABLE release_group (id int, gid uuid, name text, artist_credit int, type int);
CREATE TABLE release_group_meta (id int, first_release_date_year smallint, first_release_date_month smallint, first_release_date_day smallint);
CREATE TABLE release_group_primary_type (id int, name text);
CREATE TABLE release (id int, gid uuid, name text, artist_credit int, release_group int);
CREATE TABLE release_country (release int, date_year smallint, date_month smallint, date_day smallint);
CREATE TABLE release_unknown_country (LIKE release_country);
CREATE TABLE cover_art_archive.release_group_cover_art (release int);
CREATE TABLE cover_art_archive.cover_art (id bigint, release int, mime_type text, ordering int);
CREATE TABLE cover_art_archive.cover_art_type (id bigint, type_id int);
CREATE TABLE tag (id int, name text);
CREATE TABLE genre (name text);
CREATE TABLE recording_tag (recording int, tag int, count int);
CREATE TABLE artist_tag (artist int, tag int, count int);
CREATE TABLE release_tag (release int, tag int, count int);
CREATE TABLE release_group_tag (release_group int, tag int, count int);
CREATE TABLE medium (id int, release int);
CREATE TABLE track (medium int, recording int);

INSERT INTO artist VALUES (1, '00000000-0000-0000-0000-000000000001', 'First', 101),
                          (2, '00000000-0000-0000-0000-000000000002', 'Second', NULL),
                          (3, '00000000-0000-0000-0000-000000000003', '', 999);
INSERT INTO area_containment VALUES (100, 101);
INSERT INTO iso_3166_1 VALUES (100, 'GR');
INSERT INTO artist_credit VALUES (1, 'Both');
INSERT INTO artist_credit_name VALUES (1, 2, 1, 'Second', ''), (1, 1, 0, 'First!', ' & ');
INSERT INTO recording VALUES (4, '00000000-0000-0000-0000-000000000004', NULL, 1);
INSERT INTO recording_gid_redirect VALUES ('00000000-0000-0000-0000-000000000005', 4);
INSERT INTO release_group VALUES (6, '00000000-0000-0000-0000-000000000006', 'Group', 1, NULL);
INSERT INTO release_group_meta VALUES (6, NULL, NULL, NULL);
INSERT INTO release VALUES (7, '00000000-0000-0000-0000-000000000007', 'Release', 1, 6);
INSERT INTO medium VALUES (8, 7);
INSERT INTO track VALUES (8, 4);
INSERT INTO tag VALUES (10, 'jazz'), (11, 'live');
INSERT INTO genre VALUES ('jazz');
INSERT INTO recording_tag VALUES (4, 10, 3), (4, 11, 1);
INSERT INTO artist_tag VALUES (1, 10, 1), (2, 10, 3);
INSERT INTO release_group_tag VALUES (6, 10, 2);
INSERT INTO release_tag VALUES (7, 10, 3);
