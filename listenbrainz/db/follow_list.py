import sqlalchemy
from listenbrainz import db
from flask import current_app

def _create(connection, name, creator, private=False):
    result = connection.execute(sqlalchemy.text("""
        INSERT INTO follow_list (name, creator, private)
             VALUES (:name, :creator, :private)
          RETURNING id
    """), {
        'name': name,
        'creator': creator,
        'private': private,
    })
    return result.fetchone()['id']


def _add_users(connection, list_id, user_ids):
    connection.execute(sqlalchemy.text("""
        INSERT INTO follow_list_member (list_id, user_id, priority)
             VALUES (:list_id, :user_id, :priority)
    """), [{'list_id': list_id, 'user_id': user_id, 'priority': priority} for priority, user_id in enumerate(user_ids)])


def _remove_users(connection, list_id):
    connection.execute(sqlalchemy.text("""
        DELETE FROM follow_list_member
              WHERE list_id = :list_id
    """), {'list_id': list_id})


def _get_members(connection, list_id):
    result = connection.execute(sqlalchemy.text("""
        SELECT user_id, musicbrainz_id, created, priority
          FROM follow_list_member
          JOIN "user"
            ON follow_list_member.user_id = "user".id
         WHERE list_id = :list_id
      ORDER BY priority DESC
    """), {
        'list_id': list_id,
    })
    return [dict(row) for row in result.fetchall()]


def _get_by_creator_and_name(connection, creator, list_name):
    r = connection.execute(sqlalchemy.text("""
        SELECT id
          FROM follow_list
         WHERE creator = :creator
           AND LOWER(name) = LOWER(:list_name)
    """), {
        'creator': creator,
        'list_name': list_name,
    })

    if r.rowcount > 0:
        return r.fetchone()['id']
    else:
        return None


def _update_name(connection, list_id, name):
    connection.execute(sqlalchemy.text("""
        UPDATE follow_list
           SET last_saved = NOW(),
               name = :name
         WHERE id = :list_id
    """), {
        'list_id': list_id,
        'name': name,
    })


def save(name, creator, members, private=False):
    with db.engine.begin() as connection:
        list_id = _get_by_creator_and_name(connection, creator, name)
        if list_id:
            raise DatabaseException("List already exists")

        list_id = _create(connection, name, creator, private)
        if members:
            _add_users(connection, list_id, members)
    return list_id


def get(list_id):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, name, creator, private, created, last_saved
              FROM follow_list
             WHERE id = :list_id
        """), {
            "list_id": list_id,
        })
        current_app.logger.error(result.rowcount)
        if result.rowcount == 0:
            return None
        else:
            row = dict(result.fetchone())
            current_app.logger.error(row)
            return row


def update(list_id, name, members):
    with db.engine.begin() as connection:
        _update_name(connection, list_id, name)
        _remove_users(connection, list_id)
        if members:
            _add_users(connection, list_id, members)


def get_follow_lists(creator):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, name, creator, private
              FROM follow_list
             WHERE creator = :creator
        """), {
            'creator': creator,
        })
        return [dict(row) for row in result.fetchall()]


def get_latest(creator):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, name, creator, private
              FROM follow_list
             WHERE creator = :creator
          ORDER BY last_saved DESC
             LIMIT 1
        """), {
            'creator': creator,
        })
        if result.rowcount == 0:
            return None
        row = result.fetchone()
        return {
            'id': row['id'],
            'name': row['name'],
            'creator': row['creator'],
            'private': row['private'],
            'members': _get_members(connection, row['id']),
        }
