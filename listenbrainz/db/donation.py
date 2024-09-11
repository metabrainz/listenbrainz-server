import time
from typing import Optional

import psycopg2
import sqlalchemy
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, NullPool, text

engine: Optional[sqlalchemy.engine.Engine] = None


def init_meb_db_connection(connect_str):
    """Initializes database connection using the specified Flask app."""
    global engine
    while True:
        try:
            engine = create_engine(connect_str, poolclass=NullPool)
            break
        except psycopg2.OperationalError as e:
            print("Couldn't establish connection to db: {}".format(str(e)))
            print("Sleeping 2 seconds and trying again...")
            time.sleep(2)


def get_flairs_for_donors(db_conn, donors):
    """ Get flairs for donors. """
    musicbrainz_row_ids = {d.editor_id for d in donors}

    query = """
            SELECT u.musicbrainz_row_id
                 , u.musicbrainz_id
                 , us.flair
              FROM "user" u
         LEFT JOIN user_setting us
                ON us.user_id = u.id
             WHERE EXISTS(
                    SELECT 1
                      FROM (VALUES %s) AS t(editor_id)
                     WHERE u.musicbrainz_row_id = t.editor_id 
             )
        """
    with db_conn.connection.cursor() as cursor:
        results = execute_values(cursor, query, [(row_id,) for row_id in musicbrainz_row_ids], fetch=True)
        lb_users = {
            r[0]: {
                "musicbrainz_id": r[1],
                "flair": r[2]
            } for r in results
        }

    donors_with_flair = []
    for donor in donors:
        donation = {
            "amount": float(donor.amount),
            "currency": donor.currency,
            "donation_time": donor.payment_date.isoformat(),
        }
        user = lb_users.get(donor.editor_id)
        if user:
            donation["is_listenbrainz_user"] = True
            donation["musicbrainz_id"] = user["musicbrainz_id"]
            donation["flair"] = user["flair"]
        else:
            donation["is_listenbrainz_user"] = False
            donation["musicbrainz_id"] = donor.editor_name
            donation["flair"] = None

        donors_with_flair.append(donation)

    return donors_with_flair


def get_recent_donors(meb_conn, db_conn, count: int, offset: int):
    """ Get a list of recent donors with their flairs """
    query = """
        SELECT editor_name
             , editor_id
             , amount
             , currency
             , payment_date
          FROM payment
         WHERE editor_id IS NOT NULL
           AND is_donation = 't'
      ORDER BY payment_date DESC
         LIMIT :count
        OFFSET :offset
    """
    results = meb_conn.execute(text(query), {"count": count, "offset": offset})
    donors = results.all()

    return get_flairs_for_donors(db_conn, donors)


def get_biggest_donors(meb_conn, db_conn, count: int, offset: int):
    """ Get a list of biggest donors with their flairs """
    query = """
        SELECT editor_name
             , editor_id
             , currency
             , sum(amount) as amount
             , max(payment_date) AS payment_date
          FROM payment
         WHERE editor_id IS NOT NULL
           AND is_donation = 't'
      GROUP BY editor_name
             , editor_id
             , currency
      ORDER BY amount DESC
         LIMIT :count
        OFFSET :offset
    """

    results = meb_conn.execute(text(query), {"count": count, "offset": offset})
    donors = results.all()

    return get_flairs_for_donors(db_conn, donors)


def is_user_donor(meb_conn, musicbrainz_row_id: int):
    """ Check if the user with the given musicbrainz row id is a donor """
    query = "SELECT EXISTS(SELECT 1 FROM payment WHERE editor_id = :editor_id) AS is_donor"
    result = meb_conn.execute(text(query), {"editor_id": musicbrainz_row_id})
    row = result.first()
    return row is not None and row.is_donor
