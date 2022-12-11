import uuid
from datetime import date, timedelta
from typing import List

import psycopg2
import psycopg2.extras
from flask import current_app

from listenbrainz.db import couchdb
from listenbrainz.db.cover_art import get_caa_ids_for_release_mbids
from listenbrainz.db.model.fresh_releases import FreshRelease


def get_sitewide_fresh_releases(pivot_release_date: date, release_date_window_days: int) -> List[FreshRelease]:
    """ Fetch fresh and recent releases from the MusicBrainz DB with a given window that is days number
        of days into the past and days number of days into the future.

        Args:
            pivot_release_date: The release_date around which to fetch the fresh releases.
            release_date_window_days: The number of days into the past and future to show releases for. Must be
                                      between 1 and 30 days. If an invalid value is passed, 30 days is used.

        Returns:
            A list of FreshReleases objects
    """

    if release_date_window_days > 30 or release_date_window_days < 1:
        release_date_window_days = 30

    from_date = pivot_release_date + timedelta(days=-release_date_window_days)
    to_date = pivot_release_date + timedelta(days=release_date_window_days)

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
                ) SELECT *
                    FROM releases
                ORDER BY release_date
                       , artist_credit_name
                       , release_name
        """
    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn, \
            conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (from_date, to_date))
        result = {str(row["release_mbid"]): dict(row) for row in curs.fetchall()}

        covers = get_caa_ids_for_release_mbids(curs, result.keys())

        fresh_releases = []
        for mbid, row in result.items():
            row["caa_id"] = covers[mbid]["caa_id"]
            if covers[mbid]["caa_release_mbid"]:
                row["caa_release_mbid"] = uuid.UUID(covers[mbid]["caa_release_mbid"])
            else:
                row["caa_release_mbid"] = None
            fresh_releases.append(FreshRelease(**row))

        return fresh_releases


def insert_fresh_releases(database: str, docs: list[dict]):
    """ Insert the given fresh releases in the couchdb database. """
    for doc in docs:
        doc["_id"] = str(doc["user_id"])
    couchdb.insert_data(database, docs)


def get_fresh_releases(user_id: int):
    """ Retrieve fresh releases for given user. """
    return couchdb.fetch_data("fresh_releases", user_id)
