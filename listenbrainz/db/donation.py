import time
from typing import Optional

import psycopg2
import sqlalchemy
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, NullPool, text

engine: Optional[sqlalchemy.engine.Engine] = None

FLAIR_MONTHLY_DONATION_THRESHOLD = 5


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
    """ Given a list of donors, add information about the user's musicbrainz username and whether the user is a listenbrainz
     user and returns the updated list. """
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
            "donation": float(donor.donation),
            "currency": donor.currency,
            "donated_at": donor.payment_date.isoformat(),
            "show_flair": donor.show_flair,
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
    """ Returns a list of recent donors with their flairs """
    query = """
        SELECT editor_name
             , editor_id
             , (amount + fee) as donation
             , currency
             , payment_date
             -- check if the donation itself is eligible for flair
             -- convert days to month because by default timestamp subtraction is in days
             , bool_or(
                    (
                        (amount + fee)
                       / GREATEST(ceiling(EXTRACT(days from now() - payment_date) / 30.0), 1)
                    )
                    >= :threshold
               ) OVER (PARTITION BY editor_id) AS show_flair
          FROM payment
         WHERE editor_id IS NOT NULL
           AND is_donation = 't'
           AND (anonymous != 't' OR anonymous IS NULL)
           AND payment_date >= (NOW() - INTERVAL '1 year')
      ORDER BY payment_date DESC
         LIMIT :count
        OFFSET :offset
    """
    results = meb_conn.execute(text(query), {
        "count": count,
        "offset": offset,
        "threshold": FLAIR_MONTHLY_DONATION_THRESHOLD
    })
    donors = results.all()

    total_count_query = """
        SELECT COUNT(*)
          FROM payment
         WHERE editor_id IS NOT NULL
           AND is_donation = 't'
           AND payment_date >= (NOW() - INTERVAL '1 year')
    """

    result = meb_conn.execute(text(total_count_query))
    total_count = result.scalar()

    return get_flairs_for_donors(db_conn, donors), total_count


def get_biggest_donors(meb_conn, db_conn, count: int, offset: int):
    """ Returns a list of biggest donors with their flairs """
    query = """
        WITH select_donations AS (
        SELECT editor_name
             , editor_id
             , (amount + fee) as donation
             , currency
             , payment_date
             -- check if the donation itself is eligible for flair
             -- convert days to month because by default timestamp subtraction is in days
             , (
                 (
                    (amount + fee) 
                   / GREATEST(ceiling(EXTRACT(days from now() - payment_date) / 30.0), 1)
                 )
                 >= :threshold
               ) AS is_donation_eligible
          FROM payment
         WHERE editor_id IS NOT NULL
           AND is_donation = 't'
           AND (anonymous != 't' OR anonymous IS NULL)
           AND payment_date >= (NOW() - INTERVAL '1 year')
        )
        SELECT editor_name
             , editor_id
             , currency
             , max(payment_date) as payment_date
             , sum(donation) as donation
             , bool_or(is_donation_eligible) AS show_flair
          FROM select_donations
      GROUP BY editor_name
             , editor_id
             , currency
      ORDER BY donation DESC
         LIMIT :count
        OFFSET :offset 
    """

    results = meb_conn.execute(text(query), {
        "count": count,
        "offset": offset,
        "threshold": FLAIR_MONTHLY_DONATION_THRESHOLD
    })
    donors = results.all()

    total_count_query = """
        WITH select_donations AS (
      SELECT editor_id
           , currency
        FROM payment
        WHERE editor_id IS NOT NULL
          AND is_donation = 't'
          AND payment_date >= (NOW() - INTERVAL '1 year')
        )
       SELECT COUNT(*)
        FROM (
            SELECT editor_id
                 , currency
              FROM select_donations
          GROUP BY editor_id, currency
        ) AS total_count;
    """

    result = meb_conn.execute(text(total_count_query))
    total_count = result.scalar()

    return get_flairs_for_donors(db_conn, donors), total_count


def is_user_eligible_donor(meb_conn, musicbrainz_row_id: int):
    """ Check if the user with the given musicbrainz row id is a donor and has enough recent
     donations to be eligible for flair """
    result = are_users_eligible_donors(meb_conn, [musicbrainz_row_id])
    return result.get(musicbrainz_row_id, False)


def are_users_eligible_donors(meb_conn, musicbrainz_row_ids: list[int]):
    """ Check if the users with the given musicbrainz row ids are donors and have enough recent
    donations to be eligible for flair """
    query = """
        SELECT editor_id
             , (
                SELECT coalesce(
                            bool_or(
                                (
                                    (amount + fee)
                                   / GREATEST(ceiling(EXTRACT(days from now() - payment_date) / 30.0), 1)
                                )
                                >= :threshold)
                            , 'f'
                        )
                  FROM payment
                 WHERE editor_id = e.editor_id
                   AND is_donation = 't'
                   AND (anonymous != 't' OR anonymous IS NULL)
                   AND payment_date >= (NOW() - INTERVAL '1 year')
               ) AS show_flair
          FROM unnest(:editor_ids) as e (editor_id)
    """
    result = meb_conn.execute(text(query), {
        "editor_ids": musicbrainz_row_ids,
        "threshold": FLAIR_MONTHLY_DONATION_THRESHOLD
    })
    eligibility_map = {}
    for row in result.all():
        eligibility_map[row.editor_id] = row.show_flair
    return eligibility_map
