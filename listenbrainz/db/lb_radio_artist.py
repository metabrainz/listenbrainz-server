from collections import defaultdict
from random import randint
import uuid

from psycopg2.extras import DictCursor
from psycopg2.sql import SQL, Literal

from listenbrainz.webserver import ts_conn


def lb_radio_artist(mode: str, seed_artist: str, max_similar_artists: int, num_recordings_per_artist: int, pop_begin: float,
                    pop_end: float) -> dict[str, list[dict]]:
    """
        Fetch recordings for LB Radio's similar artists element.

        Given a seed artist mbid, find similar artists given other parameters and then return
        a dict of artist_mbids that contain lists of dict as such:
            {
              "recording_mbid": "401c1a5d-56e7-434d-b07e-a14d4e7eb83c",
              "similar_artist_mbid": "cb67438a-7f50-4f2b-a6f1-2bb2729fd538",
              "total_listen_count": 232361
            }

        Troi will take this data and complete processing it into a complete playlist.

        parameters:

        mode: LB radio mode, must be one of: easy, medium, hard.
        seed_artist: artist mbid of the seed artist for similar artists
        num_recordings_per_artist: Return up to this many recordings for each artist.
        pop_begin: Popularity range percentage lower bound. A popularity range is given to narrow down
                   the recordings into a smaller target group. The most popular track(s) on
                   LB have a pop percent of 100. The least popular tracks have a score of 0.
        pop_end: Popularity range percentage upper bound. See above.
    """
    query = SQL("""
        WITH similar_artists AS (
           SELECT CASE WHEN mbid0 = {seed_artist_mbid} THEN mbid1 ELSE mbid0 END AS similar_artist_mbid
                , sa.score
             FROM similarity.artist sa
            WHERE (mbid0 = {seed_artist_mbid} OR mbid1 = {seed_artist_mbid})
        ), knockdown AS (
           SELECT similar_artist_mbid
                , CASE WHEN similar_artist_mbid = oa.artist_mbid THEN score * oa.factor ELSE score END AS score
             FROM similar_artists sa
        LEFT JOIN similarity.overhyped_artists oa
               ON sa.similar_artist_mbid = oa.artist_mbid
        ), knockdown_with_rownum AS (
            SELECT similar_artist_mbid
                 , score
                 , ROW_NUMBER() OVER (ORDER BY score DESC) AS rownum
              FROM knockdown
          ORDER BY rownum   
             LIMIT {similar_artist_limit}
        ), select_similar_artists AS (
           SELECT similar_artist_mbid
             FROM knockdown_with_rownum
            WHERE rownum in %s
         ORDER BY rownum
        ), similar_artists_and_orig_artist AS (
           SELECT similar_artist_mbid
             FROM select_similar_artists
            UNION
           SELECT {seed_artist_mbid} AS similar_artist_mbid
        ), combine_similarity AS (
           SELECT similar_artist_mbid
                , recording_mbid
                , total_listen_count
                , total_user_count
             FROM popularity.top_recording tr
             JOIN similar_artists_and_orig_artist sao
               ON tr.artist_mbid = sao.similar_artist_mbid
            UNION ALL
           SELECT similar_artist_mbid
                , recording_mbid
                , total_listen_count
                , total_user_count
             FROM popularity.mlhd_top_recording tmr
             JOIN similar_artists_and_orig_artist sao2
               ON tmr.artist_mbid = sao2.similar_artist_mbid
        ), group_similarity AS (
           SELECT similar_artist_mbid
                , recording_mbid
                , SUM(total_listen_count) AS total_listen_count
                , SUM(total_user_count) AS total_user_count
             FROM combine_similarity
         GROUP BY similar_artist_mbid, recording_mbid
        ), top_recordings AS (
           SELECT similar_artist_mbid
                , recording_mbid
                , total_listen_count
                , PERCENT_RANK() OVER (PARTITION BY similar_artist_mbid ORDER BY total_listen_count) AS rank
             FROM group_similarity gs
         GROUP BY similar_artist_mbid, recording_mbid, total_listen_count
        ), randomize AS (
           SELECT similar_artist_mbid
                , recording_mbid
                , total_listen_count
                , rank
                , ROW_NUMBER() OVER (PARTITION BY similar_artist_mbid ORDER BY RANDOM()) AS rownum
             FROM top_recordings
            WHERE rank >= {pop_begin} and rank < {pop_end}   -- select the range of results here
        )
           SELECT similar_artist_mbid::TEXT
                , recording_mbid::TEXT
                , artist_data->'name' AS similar_artist_name
                , total_listen_count
             FROM randomize
             JOIN mapping.mb_artist_metadata_cache
               ON artist_mbid = similar_artist_mbid
            WHERE rownum <= {num_recordings_per_artist}
    """).format(
        seed_artist_mbid=Literal(uuid.UUID(seed_artist)),
        similar_artist_limit=Literal(100),
        pop_begin=Literal(pop_begin),
        pop_end=Literal(pop_end),
        num_recordings_per_artist=Literal(num_recordings_per_artist)
    )

    # This mapping determines how artists are picked from the similar artists.
    # For each mode, we have a tuple of (steps, offset) which indicates at which offset
    # down the similar artists we should start selecting and then how large the bins are
    # from which we randomly select an artist. This ensures a decent spread of artists
    # and ensures that when run repeatedly that different results are returned each time.
    step_index = {"easy": (2, 0), "medium": (4, 3), "hard": (10, 10)}
    steps, offset = step_index[mode]

    # Now select the actual similar artist offsets to pick
    artist_indexes = []
    if max_similar_artists > 0:
        for i in range(max_similar_artists):
            try:
                artist_indexes.append(randint((i * steps + offset), ((i + 1) * steps + offset)))
            except IndexError:
                break
    else:
        # Provide a row id that does not exist
        artist_indexes = [0]

    # Pass the calculated args above to postgres and run the query
    with ts_conn.connection.cursor(cursor_factory=DictCursor) as curs:
        curs.execute(query, (tuple(artist_indexes),))

        artists = defaultdict(list)
        for row in curs.fetchall():
            artists[row["similar_artist_mbid"]].append(dict(row))

    return artists
