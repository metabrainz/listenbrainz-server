import sqlalchemy

from listenbrainz import db

def create(name, user_id, follow_list, private=False):
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO follow_list (name, user_id, private)
                 VALUES (:name, :user_id, :private)
              RETURNING list_id
        """), {
            'name': name,
            'user_id': user_id,
            'private': private,
        })

        list_id = result.fetchone()['list_id']
        connection.execute(sqlalchemy.text("""
            INSERT INTO follow_list_member (list_id, user_id)
                 VALUES (:list_id, :user_id)
        """), [{'list_id': list_id, 'user_id': user_id} for user_id in follow_list])

    return list_id


def add_user(list_id, user_id):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO follow_list_member (list_id, user_id)
                 VALUES (:list_id, :user_id)
        """), {
            'list_id': list_id,
            'user_id': user_id,
        })


def get_follow_lists(user_id):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, name, creator, private
              FROM follow_list
             WHERE user_id = :user_id
        """), {
            'user_id': user_id,
        })
        return [dict(row) for row in result.fetchall()]


def get_follow_list_member(list_id):
    with db.engine.connect() as connection:
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
