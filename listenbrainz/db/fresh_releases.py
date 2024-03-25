import uuid
from datetime import date, timedelta
from typing import List

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values
from flask import current_app

from listenbrainz.db import couchdb
from listenbrainz.db.cover_art import get_caa_ids_for_release_mbids
from listenbrainz.db.model.fresh_releases import FreshRelease


def get_sitewide_fresh_releases(
        ts_conn,
        pivot_release_date: date,
        release_date_window_days: int,
        sort: str,
        past: bool,
        future: bool) -> (List[FreshRelease], int):
    """ Fetch fresh and recent releases from the MusicBrainz DB with a given window that is days number
        of days into the past and days number of days into the future.

        Args:
            ts_conn: timescale database connection
            pivot_release_date: The release_date around which to fetch the fresh releases.
            release_date_window_days: The number of days into the past and future to show releases for. Must be
                                      between 1 and 90 days. If an invalid value is passed, 90 days is used.
            sort: The sort order of the results. Must be one of "release_date", "artist_credit_name" or "release_name".
            past: Whether to show releases in the past.
            future: Whether to show releases in the future.

        Returns:
            A list of FreshReleases objects
            The total number of releases in the given window
    """

    if release_date_window_days > 90 or release_date_window_days < 1:
        release_date_window_days = 90

    from_date = pivot_release_date + \
        timedelta(days=-release_date_window_days) if past else pivot_release_date
    to_date = pivot_release_date + \
        timedelta(days=release_date_window_days) if future else pivot_release_date

    sort_order = ["release_date", "artist_credit_name", "release_name"]
    sort_order = sort_order[sort_order.index(
        sort):] + sort_order[:sort_order.index(sort)]
    sort_order_str = ", ".join(sort_order)

    query = """
                WITH releases AS (
                    SELECT DISTINCT ON (rg.id)
                           rl.id AS release_id
                         , rl.gid AS release_mbid
                         , rg.gid AS release_group_mbid
                         , rl.name AS release_name
                         , make_date(rgm.first_release_date_year,
                                      rgm.first_release_date_month,
                                      rgm.first_release_date_day) AS release_date
                         , ac.name AS artist_credit_name
                         , array_agg(distinct a.gid) AS artist_mbids
                         , rgpt.name AS release_group_primary_type
                         , rgst.name AS release_group_secondary_type
                         , array_agg(distinct t.name) AS release_tags
                      FROM release rl
                      JOIN release_group rg
                        ON rl.release_group = rg.id
                      JOIN release_group_meta rgm
                        ON rgm.id = rg.id
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
                 LEFT JOIN release_tag rt
                        ON rt.release = rl.id
                 LEFT JOIN tag t
                        ON t.id = rt.tag
                     WHERE make_date(rgm.first_release_date_year,
                                     rgm.first_release_date_month,
                                     rgm.first_release_date_day) >= %s
                       AND make_date(rgm.first_release_date_year,
                                     rgm.first_release_date_month,
                                     rgm.first_release_date_day) <= %s
                  GROUP BY rg.id
                         , release_date
                         , release_mbid
                         , release_id
                         , release_name
                         , release_date
                         , artist_credit_name
                         , release_group_primary_type
                         , release_group_secondary_type
                  ORDER BY rg.id
                         , release_date
                ), total_count AS (
                  SELECT count(*) AS total_count
                    FROM releases
                ) SELECT releases.*,
                         tc.total_count AS total_count
                    FROM releases
              CROSS JOIN total_count tc
                ORDER BY {sort_order_str};
        """.format(sort_order_str=sort_order_str)

    listen_count_query = """
                SELECT
                    release_mbid,
                    total_listen_count
                FROM
                    popularity.release
                WHERE
                    release_mbid in %s;
    """

    fresh_releases = []
    total_count = 0
    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
            mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
            ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:
        mb_curs.execute(query, (from_date, to_date))
        result = {str(row["release_mbid"]): dict(row)
                  for row in mb_curs.fetchall()}

        release_mbids = [row["release_mbid"] for row in result.values()]
        release_count_result = execute_values(
            ts_curs, listen_count_query, (tuple(release_mbids),))

        listen_counts = {row["release_mbid"]: row["total_listen_count"]
                         for row in release_count_result} if release_count_result else {}

        covers = get_caa_ids_for_release_mbids(mb_curs, result.keys())

        for mbid, row in result.items():
            if row["release_tags"] == [None]:
                row["release_tags"] = []
            row["caa_id"] = covers[mbid]["caa_id"]
            if covers[mbid]["caa_release_mbid"]:
                row["caa_release_mbid"] = uuid.UUID(
                    covers[mbid]["caa_release_mbid"])
            else:
                row["caa_release_mbid"] = None

            row["listen_count"] = listen_counts.get(mbid, 0)
            fresh_releases.append(FreshRelease(**row))
            total_count = row["total_count"]

    return fresh_releases, total_count


def insert_fresh_releases(database: str, docs: List[dict]):
    """ Insert the given fresh releases in the couchdb database. """
    for doc in docs:
        doc["_id"] = str(doc["user_id"])
    couchdb.insert_data(database, docs)


def get_fresh_releases(user_id: int):
    """ Retrieve fresh releases for given user. """
    return couchdb.fetch_data("fresh_releases", user_id)
