from datetime import datetime

from sqlalchemy import text

from listenbrainz import db


def insert(db_conn, user_id, entity, entity_mbid, until):
    """ Add an entry to do_not_recommend table for the specified user and entity until the given time. """
    query = """
        INSERT INTO recommendation.do_not_recommend (user_id, entity, entity_mbid, until)
             VALUES (:user_id, :entity, :entity_mbid, :until)
        ON CONFLICT (user_id, entity, entity_mbid)
          DO UPDATE SET until = EXCLUDED.until
    """
    until = datetime.fromtimestamp(until) if until else None
    db_conn.execute(text(query), {"user_id": user_id, "entity": entity, "entity_mbid": entity_mbid, "until": until})
    db_conn.commit()


def delete(db_conn, user_id, entity, entity_mbid):
    """ Remove an entry from the do_not_recommend table for the specified user and entity. """
    query = """
        DELETE FROM recommendation.do_not_recommend
              WHERE user_id = :user_id
                AND entity = :entity
                AND entity_mbid = :entity_mbid
    """
    db_conn.execute(text(query), {"user_id": user_id, "entity": entity, "entity_mbid": entity_mbid})
    db_conn.commit()


def get(db_conn, user_id, count, offset):
    """ Retrieve all do not recommend entries for specified user """
    query = """
        SELECT user_id
             , entity
             , entity_mbid
             , EXTRACT(epoch from until)::int AS until
             , EXTRACT(epoch from created)::int AS created
          FROM recommendation.do_not_recommend
         WHERE user_id = :user_id
           AND (until IS NULL OR until > NOW())
      ORDER BY created
         LIMIT :count
        OFFSET :offset
    """
    result = db_conn.execute(text(query), {"user_id": user_id, "count": count, "offset": offset})
    return [
        {"entity": r.entity, "entity_mbid": r.entity_mbid, "until": r.until, "created": r.created}
        for r in result.fetchall()
    ]


def get_total_count(db_conn, user_id):
    """ Get the total count of do not recommend entries for a given user """
    query = """
        SELECT count(*) as count
          FROM recommendation.do_not_recommend
         WHERE user_id = :user_id
           AND (until IS NULL OR until > NOW())
    """
    result = db_conn.execute(text(query), {"user_id": user_id})
    return result.first().count


def clear_expired(db_conn):
    """ Remove expired do-not-recommend entries

    do-not-recommend entries can optionally have an `until` value which denotes the time till which the entity
    should not be recommended to the user. Once that time has passed the entry can be cleaned up for the table.
    """
    query = "DELETE FROM recommendation.do_not_recommend WHERE until < NOW()"
    db_conn.execute(text(query))
    db_conn.commit()
