from datetime import datetime, date, time, timedelta

from more_itertools import chunked

from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME, ARTIST_CREDIT_MBID_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.listens.data import get_listens_from_dump
from listenbrainz_spark.utils import read_files_from_HDFS

RECORDINGS_PER_MESSAGE = 10000
# the duration value in seconds to use for track whose duration data in not available in MB
DEFAULT_TRACK_LENGTH = 180
# main artist in a credit are consider to weigh 1, featured artists should weigh less.
FEATURED_ARTIST_WEIGHT = 0.25


def build_sessioned_index(listen_table, metadata_table, artist_credit_table, session, max_contribution, threshold, limit, skip_threshold):
    # TODO: Handle case of unmatched recordings breaking sessions!
    return f"""
            WITH listens AS (
                SELECT l.user_id
                     , BIGINT(l.listened_at) AS listened_at
                     , CAST(COALESCE(r.length / 1000, {DEFAULT_TRACK_LENGTH}) AS BIGINT) AS duration
                     , l.artist_credit_mbids
                     , ac.artist_mbid
                     , ac.position
                     , ac.join_phrase
                     , any(ac.join_phrase IN ('feat.', 'ｆｅａｔ.', 'ft.', 'συμμ.', 'duet with', 'featuring', 'συμμετέχει', 'ｆｅａｔｕｒｉｎｇ')) OVER w AS after_ft_jp
                  FROM {listen_table} l
             LEFT JOIN {metadata_table} r
                 USING (recording_mbid)
                  JOIN {artist_credit_table} ac
                 USING (artist_credit_id)
                 WHERE l.recording_mbid IS NOT NULL
                   AND l.recording_mbid != ''
                WINDOW w AS (PARTITION BY l.user_id, listened_at, l.recording_mbid ORDER BY ac.position)
            ), ordered AS (
                SELECT user_id
                     , listened_at
                     , listened_at - LAG(listened_at, 1) OVER w - LAG(duration, 1) OVER w AS difference
                     , artist_credit_mbids
                     , artist_mbid
                     , COALESCE(IF(after_ft_jp, {FEATURED_ARTIST_WEIGHT}, 1), 1) AS similarity
                  FROM listens
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions AS (
                SELECT user_id
                     -- spark doesn't support window aggregate functions with FILTER clause
                     , COUNT_IF(difference > {session}) OVER w AS session_id
                     , LEAD(difference, 1) OVER w < {skip_threshold} AS skipped
                     , artist_credit_mbids
                     , artist_mbid
                     , similarity
                  FROM ordered
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions_filtered AS (
                SELECT user_id
                     , session_id
                     , artist_credit_mbids
                     , artist_mbid
                     , similarity
                  FROM sessions
                 WHERE NOT skipped    
            ), user_grouped_mbids AS (
                SELECT user_id
                     , IF(s1.artist_mbid < s2.artist_mbid, s1.artist_mbid, s2.artist_mbid) AS lexical_mbid0
                     , IF(s1.artist_mbid > s2.artist_mbid, s1.artist_mbid, s2.artist_mbid) AS lexical_mbid1
                     , s1.similarity * s2.similarity AS similarity
                  FROM sessions_filtered s1
                  JOIN sessions_filtered s2
                 USING (user_id, session_id)
                 WHERE s1.artist_mbid != s2.artist_mbid
                   AND s1.artist_credit_mbids != s2.artist_credit_mbids
            ), user_contribtion_mbids AS (
                SELECT user_id
                     , lexical_mbid0 AS mbid0
                     , lexical_mbid1 AS mbid1
                     , LEAST(SUM(similarity), {max_contribution}) AS part_score
                  FROM user_grouped_mbids
              GROUP BY user_id
                     , lexical_mbid0
                     , lexical_mbid1
            ), thresholded_mbids AS (
                SELECT mbid0
                     , mbid1
                     , BIGINT(SUM(part_score)) AS score
                  FROM user_contribtion_mbids
              GROUP BY mbid0
                     , mbid1  
                HAVING score > {threshold}
            ), ranked_mbids AS (
                SELECT mbid0
                     , mbid1
                     , score
                     , rank() OVER w AS rank
                  FROM thresholded_mbids
                WINDOW w AS (PARTITION BY mbid0 ORDER BY score DESC)     
            )   SELECT mbid0
                     , mbid1
                     , score
                  FROM ranked_mbids
                 WHERE rank <= {limit}   
    """


def main(days, session, contribution, threshold, limit, skip, is_production_dataset):
    """ Generate similar artists based on user listening sessions.

    Args:
        days: the number of days of listens to consider for calculating listening sessions
        session: the max time difference between two listens in a listening session
        contribution: the max contribution a user's listens can make to a recording pair's similarity score
        threshold: the minimum similarity score for two recordings to be considered similar
        limit: the maximum number of similar recordings to request for a given recording
            (this limit is instructive only, upto 2x number of recordings may be returned)
        skip: the minimum threshold in seconds to mark a listen as skipped. we cannot just mark a negative difference
            as skip because there may be a difference in track length in MB and music services and also issues in
            timestamping listens.
        is_production_dataset: only determines how the dataset is stored in ListenBrainz database.
    """
    to_date = datetime.combine(date.today(), time.min)
    from_date = to_date + timedelta(days=-days)

    table = "artist_similarity_listens"
    metadata_table = "recording_length"
    artist_credit_table = "artist_credit"

    get_listens_from_dump(from_date, to_date).createOrReplaceTempView(table)

    metadata_df = read_files_from_HDFS(RECORDING_LENGTH_DATAFRAME)
    metadata_df.createOrReplaceTempView(metadata_table)

    artist_credit_df = read_files_from_HDFS(ARTIST_CREDIT_MBID_DATAFRAME)
    artist_credit_df.createOrReplaceTempView(artist_credit_table)

    skip_threshold = -skip
    query = build_sessioned_index(table, metadata_table, artist_credit_table, session, contribution, threshold, limit, skip_threshold)
    data = run_query(query).toLocalIterator()

    algorithm = f"session_based_days_{days}_session_{session}_contribution_{contribution}_threshold_{threshold}_limit_{limit}_skip_{skip}"

    if is_production_dataset:
        yield {
            "type": "similarity_artist_start",
            "algorithm": algorithm
        }

    for entries in chunked(data, RECORDINGS_PER_MESSAGE):
        items = [row.asDict() for row in entries]
        yield {
            "type": "similarity_artist",
            "algorithm": algorithm,
            "data": items,
            "is_production_dataset": is_production_dataset
        }

    if is_production_dataset:
        yield {
            "type": "similarity_artist_end",
            "algorithm": algorithm
        }
