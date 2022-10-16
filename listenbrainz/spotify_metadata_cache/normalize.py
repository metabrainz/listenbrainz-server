#!/usr/bin/env python3

import logging
import psycopg2

from listenbrainz import config


query = """
WITH extract_albums AS (
         SELECT id
              , data->>'id' AS spotify_id
              , data->>'name' AS name
              , data->>'album_type' AS type
              , data->>'release_date' AS release_date
              , data->'tracks' AS tracks
              , data->'artists' AS artists
              , data - '{tracks,artists}'::text[] AS album_data
              , last_refresh
              , expires_at
           FROM mapping.spotify_metadata_cache
          WHERE id > %s
       ORDER BY id
     FETCH NEXT 50000 ROWS ONLY
), insert_albums AS (
    INSERT INTO spotify_cache.album (spotify_id, name, type, release_date, last_refresh, expires_at, data)
         SELECT spotify_id
              , name
              , type
              , release_date
              , last_refresh
              , expires_at
              , album_data
           FROM extract_albums
), extract_album_artists AS (
         SELECT spotify_id AS spotify_album_id
              , a->>'id' AS spotify_artist_id
              , a->>'name' AS name
              , a AS artist_data
              , position
           FROM extract_albums, jsonb_array_elements(artists) WITH ORDINALITY expanded(a, position)
), insert_album_artists AS (
    INSERT INTO spotify_cache.artist (spotify_id, name, data)
         SELECT DISTINCT
                spotify_artist_id
              , name
              , artist_data
           FROM extract_album_artists
    ON CONFLICT (spotify_id) DO NOTHING
), insert_rel_album_artist AS (
    INSERT INTO spotify_cache.rel_album_artist (album_id, artist_id, position)
         SELECT spotify_album_id
              , spotify_artist_id
              , position
           FROM extract_album_artists
), extract_album_tracks AS (
         SELECT spotify_id AS spotify_album_id
              , t->>'id' AS spotify_track_id
              , t->>'name' AS name
              , (t->'track_number')::int AS track_number
              , t->'artists' AS track_artists
              , t - 'artists' AS track_data
           FROM extract_albums, jsonb_array_elements(tracks) t
), insert_album_tracks AS (
    INSERT INTO spotify_cache.track (spotify_id, name, track_number, album_id, data)
         SELECT spotify_track_id
              , name
              , track_number
              , spotify_album_id
              , track_data
           FROM extract_album_tracks
), extract_track_artists AS (
         SELECT spotify_track_id
              , a->>'id' AS spotify_artist_id
              , a->>'name' AS name
              , a AS artist_data
              , position
           FROM extract_album_tracks, jsonb_array_elements(track_artists) WITH ORDINALITY expanded(a, position)
), insert_track_artists AS (
    INSERT INTO spotify_cache.artist (spotify_id, name, data)
         SELECT DISTINCT
                spotify_artist_id
              , name
              , artist_data
           FROM extract_track_artists
    ON CONFLICT (spotify_id) DO NOTHING
), insert_rel_track_artist AS (
    INSERT INTO spotify_cache.rel_track_artist (track_id, artist_id, position)
        SELECT spotify_track_id
             , spotify_artist_id
             , position
        FROM extract_track_artists
) SELECT max(id) AS max_row_id FROM extract_albums;
"""


def normalize_spotify_cache():
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)
    logging.info("Starting normalization")

    last_row_id = 0
    with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as conn, conn.cursor() as curs:
        while True:
            curs.execute(query, (last_row_id,))
            conn.commit()
            row = curs.fetchone()
            if not row or row[0] is None:
                break
            last_row_id = row[0]
            logging.info("Last inserted row id: %s", last_row_id)

    logging.info("Completed normalization")


if __name__ == '__main__':
    normalize_spotify_cache()
