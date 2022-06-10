import json
from datetime import timedelta
from pathlib import Path

from more_itertools import chunked
from pyspark import Row

import listenbrainz_spark
from listenbrainz_spark.schema import release_radar_schema
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_latest_listen_ts, get_listens_from_new_dump

USERS_PER_MESSAGE = 5


def load_all_releases():
    with Path(__file__).parent.joinpath("release.json").open() as f:
        data = json.load(f)

        releases = []
        for release in data:
            releases.append(Row(
                date=release["date"],
                artist_credit_name=release["artist_credit_name"],
                artist_mbids=release["artist_mbids"],
                release_name=release["release_name"],
                release_mbid=release["release_mbid"],
                release_group_primary_type=release["release_group_primary_type"],
                release_group_secondary_type=release["release_group_secondary_type"]
            ))

        return listenbrainz_spark.session.createDataFrame(
            releases,
            schema=release_radar_schema
        )


def get_query():
    return """
        WITH artists AS (
            SELECT DISTINCT explode(artist_mbids) AS artist_mbid
              FROM release_radar_releases
        ), exploded_listens AS (
            SELECT user_id
                 , explode(artist_credit_mbids) AS artist_mbid
              FROM release_radar_listens
        ), artist_discovery AS (
            SELECT user_id
                 , artist_mbid
                 , count(*) AS partial_confidence
              FROM exploded_listens
              JOIN artists
             USING (artist_mbid)
          GROUP BY user_id, artist_mbid
        ), filtered_releases AS (
            SELECT ad.user_id
                 , rr.release_name
                 , rr.release_mbid
                 , rr.artist_credit_name
                 , rr.artist_mbids
                 , rr.date
                 , rr.release_group_primary_type
                 , rr.release_group_secondary_type
                 , SUM(partial_confidence) AS confidence
              FROM artist_discovery ad
              JOIN release_radar_releases rr
                ON array_contains(rr.artist_mbids, ad.artist_mbid)
          GROUP BY ad.user_id
                 , rr.release_name
                 , rr.release_mbid
                 , rr.artist_credit_name
                 , rr.artist_mbids
                 , rr.date
                 , rr.release_group_primary_type
                 , rr.release_group_secondary_type
        )
        SELECT user_id
             , array_sort(
                    collect_list(
                        struct(
                            release_name
                          , release_mbid
                          , artist_credit_name
                          , artist_mbids
                          , date
                          , release_group_primary_type
                          , release_group_secondary_type
                          , confidence
                        )
                    )
                   , (left, right) -> CASE
                                      WHEN left.confidence > right.confidence THEN -1
                                      WHEN left.confidence < right.confidence THEN  1
                                      ELSE 0
                                      END
                    -- sort in descending order of confidence              
               ) AS releases
          FROM filtered_releases
      GROUP BY user_id      
    """


def main(days: int):
    to_date = get_latest_listen_ts()
    from_date = to_date + timedelta(days=-days)
    get_listens_from_new_dump(from_date, to_date) \
        .createOrReplaceTempView("release_radar_listens")

    load_all_releases().createOrReplaceTempView("release_radar_releases")

    itr = run_query(get_query()).toLocalIterator()
    for rows in chunked(itr, USERS_PER_MESSAGE):
        yield {
            "type": "release_radar",
            "data": [row.asDict(recursive=True) for row in rows]
        }


"""
    SELECT DISTINCT rl.gid AS release_mbid
                  , rl.name AS release_name
                  , rgpt.name AS release_group_primary_type
                  , rgst.name AS release_group_secondary_type
                  , rc.year || '-' || rc.month || '-' || rc.day AS date
                  , ac.name AS artist_credit_name
                  , array_agg(distinct a.gid) AS artist_mbids
              FROM release rl
              JOIN release_first_release_date rc
                ON rc.release = rl.id
              JOIN release_group rg
                ON rl.release_group = rg.id
         LEFT JOIN release_group_primary_type rgpt
                ON rg.type = rgpt.id
         LEFT JOIN release_group_secondary_type_join rgstj
                ON rgstj.release_group = rg.id
         LEFT JOIN release_group_secondary_type rgst
                ON rgstj.secondary_type = rgst.id
              JOIN artist_credit ac
                ON rl.artist_credit = ac.id
              JOIN artist_credit_name acn
                ON acn.artist_credit = ac.id
              JOIN artist a
                ON acn.artist = a.id
             WHERE make_date(rc.year, rc.month, rc.day) >= '2022-05-15'
               AND make_date(rc.year, rc.month, rc.day) <= '2022-06-15' 
          GROUP BY release_mbid, release_name, date, artist_credit_name, release_group_primary_type, release_group_secondary_type
          ORDER BY date, artist_credit_name;
"""

