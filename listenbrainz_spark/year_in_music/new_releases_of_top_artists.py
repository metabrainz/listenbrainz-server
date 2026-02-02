from datetime import datetime, date, time

from more_itertools import chunked

from listenbrainz_spark.postgres.release_group import create_release_group_metadata_cache, get_release_group_metadata_cache

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.listens.data import get_listens_from_dump

USERS_PER_MESSAGE = 500
MAX_RELEASES_PER_ARTIST = 5


def get_new_releases_of_top_artists(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    get_listens_from_dump(from_date, to_date).createOrReplaceTempView("listens")

    create_release_group_metadata_cache()
    cache_table = get_release_group_metadata_cache()

    new_releases = run_query(_get_new_releases_of_top_artists(year, cache_table))

    for rows in chunked(new_releases.toLocalIterator(), USERS_PER_MESSAGE):
        stats = []
        for row in rows:
            data = row.asDict(recursive=True)
            stats.append({
                "user_id": data["user_id"],
                "data": data["new_releases"]
            })
        yield {
            "type": "year_in_music_new_releases_of_top_artists",
            "year": year,
            "data": stats
        }


def _get_new_releases_of_top_artists(year, cache_table):
    # instead of exploding the artist mbids, it is possible to use arrays_overlap on the two artist credit mbids
    # however in that case spark will do a BroadcastNestedLoopJoin which is very slow (takes 3 hours). the query
    # below using equality on artist mbid takes 2 minutes.
    return f"""
        WITH artist_counts as (
            SELECT user_id
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM listens
             WHERE artist_credit_mbids IS NOT NULL
          GROUP BY user_id
                 , artist_credit_mbids
        ), top_artists AS (
            SELECT user_id
                 , artist_credit_mbids
                 , row_number() OVER(PARTITION BY user_id ORDER BY listen_count DESC) AS row_number
              FROM artist_counts
        ), top_50_artists AS (
            SELECT user_id
                 , explode(artist_credit_mbids) AS artist_mbid
              FROM top_artists
             WHERE row_number <= 50   
        ), release_groups_of_year AS (
            SELECT title
                 , artist_credit_name
                 , release_group_mbid
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , artists
                 , primary_type
                 , explode(artist_credit_mbids) AS artist_mbid
              FROM {cache_table}
             WHERE first_release_date_year = {year}
        ), matched_releases AS (
            SELECT t50a.user_id
                 , rg.title
                 , rg.artist_credit_name
                 , rg.release_group_mbid
                 , rg.artist_credit_mbids
                 , rg.artists
                 , rg.caa_id
                 , rg.caa_release_mbid
                 , rg.primary_type
                 , t50a.artist_mbid
              FROM release_groups_of_year rg
              JOIN top_50_artists t50a
                ON rg.artist_mbid = t50a.artist_mbid
        ), ranked_releases AS (
            -- Rank releases per user per artist
            -- Priority: Album (1) > EP (2) > Single (3) > Other (4) > Broadcast (5)
            -- Then by release_group_mbid for consistency
            SELECT user_id
                 , title
                 , artist_credit_name
                 , release_group_mbid
                 , artist_credit_mbids
                 , artists
                 , caa_id
                 , caa_release_mbid
                 , row_number() OVER(
                     PARTITION BY user_id, artist_mbid 
                     ORDER BY 
                         CASE 
                             WHEN primary_type = 'Album' THEN 1
                             WHEN primary_type = 'EP' THEN 2
                             WHEN primary_type = 'Single' THEN 3
                             WHEN primary_type = 'Other' THEN 4
                             WHEN primary_type = 'Broadcast' THEN 5
                         END ASC,
                         release_group_mbid ASC
                   ) AS release_rank
              FROM matched_releases
        ), limited_releases AS (
            -- Keep only top N per artist
            SELECT user_id
                 , title
                 , artist_credit_name
                 , release_group_mbid
                 , artist_credit_mbids
                 , artists
                 , caa_id
                 , caa_release_mbid
              FROM ranked_releases
             WHERE release_rank <= {MAX_RELEASES_PER_ARTIST}
        )
            SELECT user_id
                 , collect_set(
                        struct(
                           title
                         , artist_credit_name
                         , release_group_mbid
                         , artist_credit_mbids
                         , artists
                         , caa_id
                         , caa_release_mbid
                        )
                    ) AS new_releases
              FROM limited_releases
          GROUP BY user_id
    """
