from collections import defaultdict
import json
from random import randint
from typing import List

from flask import current_app
import psycopg2
from psycopg2.extras import DictCursor

SIMILARITY_ALGORITHM = "session_based_days_7500_session_300_contribution_3_threshold_10_limit_100_filter_True_skip_30"

# TODO:
#  Add this table creation:
# create table similarity.overhyped_artists (id serial, artist_mbid UUID NOT NULL, factor FLOAT);
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d', .3);  -- The Beatles
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('83d91898-7763-47d7-b03b-b92132375c47', .3);  -- Pink Floyd
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('a74b1b7f-71a5-4011-9441-d0b5e4122711', .3);  -- Radiohead
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('8bfac288-ccc5-448d-9573-c33ea2aa5c30', .3);  -- Red Hot Chili Peppers
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('9c9f1380-2516-4fc9-a3e6-f9f61941d090', .3);  -- Muse
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('cc197bad-dc9c-440d-a5b5-d52ba2e14234', .3);  -- Coldplay
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('65f4f0c5-ef9e-490c-aee3-909e7ae6b2ab', .3);  -- Metallica
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('5b11f4ce-a62d-471e-81fc-a69a8278c7da', .3);  -- Nirvana
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('f59c5520-5f46-4d2c-b2c4-822eabf53419', .3);  -- Linkin Park
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('cc0b7089-c08d-4c10-b6b0-873582c17fd6', .3);  -- System of a Down
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('ebfc1398-8d96-47e3-82c3-f782abcdb13d', .3);  -- Beach boys
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('ba0d6274-db14-4ef5-b28d-657ebde1a396', .3);  -- Smashing pumpkins
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('87c5dedd-371d-4a53-9f7f-80522fb7f3cb', .3);  -- Björk
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('5441c29d-3602-4898-b1a1-b77fa23b8e50', .3);  -- David Bowie
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('69ee3720-a7cb-4402-b48d-a02c366f2bcf', .3);  -- The Cure
#INSERT INTO similarity.overhyped_artists (artist_mbid, factor) VALUES ('ea4dfa26-f633-4da6-a52a-f49ea4897b58', .3);  -- R.E.M


def lb_radio_artist(mode: str, seed_artist: str, max_similar_artists: int, num_recordings_per_artist: int, begin_percentage: float,
                    end_percentage: float) -> List[dict]:

    query = """WITH mbids(mbid, score) AS (
                               VALUES %s
                           ), similar_artists AS (
                               SELECT CASE WHEN mbid0 = mbid::UUID THEN mbid1::TEXT ELSE mbid0::TEXT END AS similar_artist_mbid
                                    , sa.score
                                    , ROW_NUMBER() OVER (PARTITION BY mbid ORDER BY sa.score DESC) AS rownum
                                 FROM similarity.artist sa
                                 JOIN mbids
                                   ON TRUE
                                WHERE (mbid0 = mbid::UUID OR mbid1 = mbid::UUID)
                           ), knockdown AS (
                               SELECT similar_artist_mbid
                                    , CASE WHEN similar_artist_mbid = oa.artist_mbid::TEXT THEN score * oa.factor ELSE score END AS score   
                                    , rownum
                                 FROM similar_artists sa
                            LEFT JOIN similarity.overhyped_artists oa
                                   ON sa.similar_artist_mbid = oa.artist_mbid::TEXT
                             ORDER BY rownum
                                LIMIT %s
                           ), select_similar_artists AS (
                               SELECT similar_artist_mbid
                                    , score
                                 FROM knockdown
                                WHERE rownum in %s
                                ORDER BY rownum
                           ), similar_artists_and_orig_artist AS (
                               SELECT *
                                 FROM select_similar_artists
                                UNION
                               SELECT *
                                 FROM mbids
                           ), combine_similarity AS (
                               SELECT similar_artist_mbid
                                    , artist_mbid
                                    , recording_mbid
                                    , total_listen_count
                                    , total_user_count
                                 FROM popularity.top_recording tr
                                 JOIN similar_artists_and_orig_artist sao
                                   ON tr.artist_mbid = sao.similar_artist_mbid::UUID
                                UNION ALL
                               SELECT similar_artist_mbid
                                    , artist_mbid
                                    , recording_mbid
                                    , total_listen_count
                                    , total_user_count
                                 FROM popularity.mlhd_top_recording tmr
                                 JOIN similar_artists_and_orig_artist sao2
                                   ON tmr.artist_mbid = sao2.similar_artist_mbid::UUID
                           ), group_similarity AS (
                               SELECT similar_artist_mbid
                                    , artist_mbid
                                    , recording_mbid
                                    , SUM(total_listen_count) AS total_listen_count
                                    , SUM(total_user_count) AS total_user_count
                                 FROM combine_similarity
                             GROUP BY recording_mbid, artist_mbid, similar_artist_mbid
                           ), top_recordings AS (
                               SELECT sa.similar_artist_mbid
                                    , gs.recording_mbid
                                    , total_listen_count
                                    , PERCENT_RANK() OVER (PARTITION BY sa.similar_artist_mbid
                                                               ORDER BY sa.similar_artist_mbid, total_listen_count ) AS rank
                                 FROM group_similarity gs
                                 JOIN similar_artists_and_orig_artist sa
                                   ON sa.similar_artist_mbid::UUID = gs.artist_mbid
                             GROUP BY sa.similar_artist_mbid, gs.total_listen_count, gs.recording_mbid
                           ), randomize AS (
                               SELECT similar_artist_mbid
                                    , recording_mbid
                                    , total_listen_count
                                    , rank
                                    , ROW_NUMBER() OVER (PARTITION BY similar_artist_mbid ORDER BY RANDOM()) AS rownum 
                                 FROM top_recordings
                                WHERE rank >= %s and rank < %s   -- select the range of results here
                           )
                               SELECT similar_artist_mbid::TEXT
                                    , recording_mbid
                                    , total_listen_count
                                 FROM randomize
                                WHERE rownum < %s"""

    # The query requires a count, which is safe to leave 0
    seed_artist = (seed_artist, 0)
    similar_artist_limit = 100
    step_index = {"easy": (2, 0), "medium": (4, 3), "hard": (10, 10)}
    steps, offset = step_index[mode]

    artist_indexes = []
    for i in range(max_similar_artists):
        try:
            artist_indexes.append(randint((i * steps + offset), ((i + 1) * steps + offset)))
        except IndexError:
            break
    with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as conn, conn.cursor(cursor_factory=DictCursor) as curs:
        curs.execute(
            query,
            (seed_artist, similar_artist_limit, tuple(artist_indexes), begin_percentage, end_percentage, num_recordings_per_artist))

        artists = defaultdict(list)
        for row in curs.fetchall():
            artists[row["similar_artist_mbid"]].append(dict(row))

    return artists
