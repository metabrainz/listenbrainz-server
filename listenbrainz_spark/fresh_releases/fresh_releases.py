from datetime import timedelta, datetime
from typing import Optional

import requests
from more_itertools import chunked
from pyspark import Row

import listenbrainz_spark
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.schema import fresh_releases_schema
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.listens.data import get_listens_from_dump, get_latest_listen_ts

USERS_PER_MESSAGE = 5


FRESH_RELEASES_ENDPOINT = "https://api.listenbrainz.org/1/explore/fresh-releases/?days=90"


def load_all_releases():
    response = requests.get(FRESH_RELEASES_ENDPOINT)
    data = response.json()

    releases = []
    for release in data["payload"]["releases"]:
        releases.append(Row(
            release_date=release["release_date"],
            artist_credit_name=release["artist_credit_name"],
            artist_mbids=release["artist_mbids"],
            release_name=release["release_name"],
            release_mbid=release["release_mbid"],
            release_group_mbid=release["release_group_mbid"],
            release_group_primary_type=release.get("release_group_primary_type"),
            release_group_secondary_type=release.get("release_group_secondary_type"),
            release_tags=release.get("release_tags"),
            listen_count=release.get("listen_count"),
            caa_id=release.get("caa_id"),
            caa_release_mbid=release.get("caa_release_mbid"),
        ))

    return listenbrainz_spark.session.createDataFrame(releases, schema=fresh_releases_schema)


def get_query(threshold):
    return f"""
        WITH exploded_fresh_releases AS (
            SELECT rr.*
                 , explode(artist_mbids) AS artist_mbid
              FROM fresh_releases rr
        ), exploded_listens AS (
            SELECT user_id
                 , explode(artist_credit_mbids) AS artist_mbid
              FROM fresh_releases_listens
        ), filtered_releases AS (
            SELECT el.user_id
                 , rr.release_name
                 , rr.release_mbid
                 , rr.release_group_mbid
                 , rr.artist_credit_name
                 , rr.artist_mbids
                 , rr.release_date
                 , rr.release_group_primary_type
                 , rr.release_group_secondary_type
                 , rr.caa_id
                 , rr.caa_release_mbid
                 , rr.release_tags
                 , rr.listen_count
                 , count(*) AS confidence
              FROM exploded_listens el
              JOIN exploded_fresh_releases rr
             USING (artist_mbid)
          GROUP BY el.user_id
                 , rr.release_name
                 , rr.release_mbid
                 , rr.release_group_mbid
                 , rr.artist_credit_name
                 , rr.artist_mbids
                 , rr.release_date
                 , rr.release_group_primary_type
                 , rr.release_group_secondary_type
                 , rr.caa_id
                 , rr.caa_release_mbid
                 , rr.release_tags
                 , rr.listen_count
        )
        SELECT user_id
             , array_sort(
                    collect_list(
                        struct(
                            release_name
                          , release_mbid
                          , release_group_mbid
                          , artist_credit_name
                          , artist_mbids
                          , release_date
                          , release_group_primary_type
                          , release_group_secondary_type
                          , caa_id
                          , caa_release_mbid
                          , release_tags
                          , listen_count
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
         WHERE confidence >= {threshold}
      GROUP BY user_id      
    """


def main(days: Optional[int], database: str, threshold: int):
    to_date = get_latest_listen_ts()
    if days:
        from_date = to_date + timedelta(days=-days)
    else:
        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    get_listens_from_dump(from_date, to_date) \
        .createOrReplaceTempView("fresh_releases_listens")

    load_all_releases().createOrReplaceTempView("fresh_releases")

    yield {
        "type": "couchdb_data_start",
        "database": database
    }

    itr = run_query(get_query(threshold)).toLocalIterator()
    for rows in chunked(itr, USERS_PER_MESSAGE):
        entries = []
        for row in rows:
            entry = row.asDict(recursive=True)
            entries.append(entry)
        yield {
            "type": "fresh_releases",
            "database": database,
            "data": entries
        }

    yield {
        "type": "couchdb_data_end",
        "database": database
    }
