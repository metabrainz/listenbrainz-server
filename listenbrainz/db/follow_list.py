import sqlalchemy
from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException
from flask import current_app

import listenbrainz.db.user as db_user

def _create(connection, name, creator, member, private=False):
    result = connection.execute(sqlalchemy.text("""
        INSERT INTO follow_list (name, creator, private, member)
             VALUES (:name, :creator, :private, :member)
          RETURNING id
    """), {
        'name': name,
        'creator': creator,
        'private': private,
        'member': member,
    })
    return result.fetchone()['id']


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


def save(name, creator, member, private=False):
    with db.engine.begin() as connection:
        list_id = _get_by_creator_and_name(connection, creator, name)
        if list_id:
            raise DatabaseException("List already exists")

        list_id = _create(connection, name, creator, member, private)
    return list_id


def get(list_id):
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, name, creator, private, created, last_saved, member
              FROM follow_list
             WHERE id = :list_id
        """), {
            "list_id": list_id,
        })
        if result.rowcount == 0:
            return None
        else:
            row = dict(result.fetchone())
            row['member'] = db_user.get_users_in_order(row['member'])
            return row


def update(list_id, name, member):
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE follow_list
               SET name = :name,
                   member = :member,
                   last_saved = NOW()
             WHERE id = :list_id
        """), {
            'list_id': list_id,
            'name': name,
            'member': member,
        })


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
            SELECT id, name, creator, private, member
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
            'member': db_user.get_users_in_order(row['member']),
        }
