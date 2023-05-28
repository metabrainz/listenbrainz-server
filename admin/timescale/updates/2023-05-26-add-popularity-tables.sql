BEGIN;

CREATE TABLE popularity.recording (
    recording_mbid          UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.artist (
    artist_mbid             UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.release (
    release_mbid            UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.top_recording (
    artist_mbid             UUID NOT NULL,
    recording_mbid          UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.top_release (
    artist_mbid             UUID NOT NULL,
    release_mbid            UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE INDEX popularity_recording_listen_count_idx ON popularity.recording (total_listen_count) INCLUDE (recording_mbid);
CREATE INDEX popularity_recording_user_count_idx ON popularity.recording (total_user_count) INCLUDE (recording_mbid);

CREATE INDEX popularity_artist_listen_count_idx ON popularity.artist (total_listen_count) INCLUDE (artist_mbid);
CREATE INDEX popularity_artist_user_count_idx ON popularity.artist (total_user_count) INCLUDE (artist_mbid);

CREATE INDEX popularity_release_listen_count_idx ON popularity.release (total_listen_count) INCLUDE (release_mbid);
CREATE INDEX popularity_release_user_count_idx ON popularity.release (total_user_count) INCLUDE (release_mbid);

CREATE INDEX popularity_top_recording_artist_mbid_listen_count_idx ON popularity.top_recording (artist_mbid, total_listen_count) INCLUDE (recording_mbid);
CREATE INDEX popularity_top_recording_artist_mbid_user_count_idx ON popularity.top_recording (artist_mbid, total_user_count) INCLUDE (recording_mbid);

CREATE INDEX popularity_top_release_artist_mbid_listen_count_idx ON popularity.top_release (artist_mbid, total_listen_count) INCLUDE (release_mbid);
CREATE INDEX popularity_top_release_artist_mbid_user_count_idx ON popularity.top_release (artist_mbid, total_user_count) INCLUDE (release_mbid);

COMMIT;
