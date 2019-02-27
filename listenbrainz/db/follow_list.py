import sqlalchemy
from listenbrainz import db

def _create(connection, name, creator, private=False):
    result = connection.execute(sqlalchemy.text("""
        INSERT INTO follow_list (name, creator, private, last_listened)
             VALUES (:name, :creator, :private, NOW())
          RETURNING id
    """), {
        'name': name,
        'creator': creator,
        'private': private,
    })
    return result.fetchone()['id']


def _add_users(connection, list_id, user_ids):
    connection.execute(sqlalchemy.text("""
        INSERT INTO follow_list_member (list_id, user_id)
             VALUES (:list_id, :user_id)
    """), [{'list_id': list_id, 'user_id': user_id} for user_id in user_ids])


def _remove_users(connection, list_id, user_ids):
    connection.execute(sqlalchemy.text("""
        DELETE FROM follow_list_member
              WHERE list_id = :list_id
                AND user_id IN :user_ids
    """), {'list_id': list_id, 'user_ids': tuple(user_ids)})


def _get_members(connection, list_id):
    result = connection.execute(sqlalchemy.text("""
        SELECT user_id, musicbrainz_id, created
          FROM follow_list_member
          JOIN "user"
            ON follow_list_member.user_id = "user".id
         WHERE list_id = :list_id
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


def save(name, creator, members, private=False):
    with db.engine.begin() as connection:
        list_id = _get_by_creator_and_name(connection, creator, name)
        if not list_id:
            list_id = _create(connection, name, creator, private)

        old_members = set(member['user_id'] for member in _get_members(connection, list_id))
        members = set(members)
        users_to_add = members - old_members
        if users_to_add:
            _add_users(connection, list_id, users_to_add)
        users_to_remove = old_members - members
        if users_to_remove:
            _remove_users(connection, list_id, users_to_remove)

    return list_id


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
          ORDER BY last_listened DESC NULLS LAST
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
