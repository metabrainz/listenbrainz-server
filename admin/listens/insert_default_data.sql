BEGIN;

-- Insert the overhyped artists table
-- TODO: Should this be added to table dumps or do we wait until the other similarity tables get dumped as well?

INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d', .3);  -- The Beatles
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('83d91898-7763-47d7-b03b-b92132375c47', .3);  -- Pink Floyd
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('a74b1b7f-71a5-4011-9441-d0b5e4122711', .3);  -- Radiohead
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('8bfac288-ccc5-448d-9573-c33ea2aa5c30', .3);  -- Red Hot Chili Peppers
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('9c9f1380-2516-4fc9-a3e6-f9f61941d090', .3);  -- Muse
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('cc197bad-dc9c-440d-a5b5-d52ba2e14234', .3);  -- Coldplay
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('65f4f0c5-ef9e-490c-aee3-909e7ae6b2ab', .3);  -- Metallica
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('5b11f4ce-a62d-471e-81fc-a69a8278c7da', .3);  -- Nirvana
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('f59c5520-5f46-4d2c-b2c4-822eabf53419', .3);  -- Linkin Park
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('cc0b7089-c08d-4c10-b6b0-873582c17fd6', .3);  -- System of a Down
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('ebfc1398-8d96-47e3-82c3-f782abcdb13d', .3);  -- Beach boys
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('ba0d6274-db14-4ef5-b28d-657ebde1a396', .3);  -- Smashing pumpkins
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('87c5dedd-371d-4a53-9f7f-80522fb7f3cb', .3);  -- Björk
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('5441c29d-3602-4898-b1a1-b77fa23b8e50', .3);  -- David Bowie
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('69ee3720-a7cb-4402-b48d-a02c366f2bcf', .3);  -- The Cure
INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('ea4dfa26-f633-4da6-a52a-f49ea4897b58', .3);  -- R.E.M

COMMIT;
