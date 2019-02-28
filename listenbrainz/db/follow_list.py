import sqlalchemy
from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException
from flask import current_app

import listenbrainz.db.user as db_user

def _create(connection, name, creator, member, private=False):
    """ Create a new follow list.

    Args:
        connection: an sqlalchemy database connection
        name: the name of the list
        creator (int): the row ID of the list creator
        member ([int]): an ordered list of members of the follow list

    Returns: id (int): the id of the newly created list
    """
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
    """ Gets follow list created by `creator` with name `list_name`.

    Args:
        connection: an sqlalchemy database connection
        creator (int): the row ID of the list creator
        list_name (str): the name of the list

    Returns: the row ID of the list, None otherwise
    """
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
    """ Create a new list in the database, with checks for duplicates.

    Args:
        name (str): the name of the list,
        creator (int): the row ID of the list creator,
        member ([int]): an ordered list of the row IDs of members of the list

    Returns: (int): the row ID of the list

    Raises: DatabaseException if list with same name for the same creator already exists
    """
    with db.engine.begin() as connection:
        list_id = _get_by_creator_and_name(connection, creator, name)
        if list_id:
            raise DatabaseException("List already exists")

        list_id = _create(connection, name, creator, member, private)
    return list_id


def get(list_id):
    """ Get follow list with specified ID.

    Args:
        list_id (int): the row ID of the follow list

    Returns: dict representing the list if it exists, None otherwise

    The format of the dict is:
        {
            'id': int,
            'name': str,
            'creator': int,
            'private': bool,
            'last_saved': datetime,
            'created': datetime,
            'member: [{
                'id': (int) user_id,
                'musicbrainz_id': (str),
            }]
        }
    """

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
    """ Update the name and members of the list with specified ID.

    Args:
        list_id (int): the row ID of th follow list
        name (str): the new name of the list
        member ([int]): ordered list of row IDs of new members of the follow list
    """
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
    """ Get all follow lists created by `creator`

    Args:
        creator (int): the row ID of the creator

    Returns: list of dicts with each dict representing a follow list

    Each dict has the following format:
        {
            'id': int,
            'name': str,
            'private': bool,
            'creator': int (user id)
        }
    """
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
    """ Get the list created by `creator` that was most recently saved.

    This list is used as the default list loaded by the `/follow` page.

    Args:
        creator (int): the row ID of the creator

    Returns: the most recently saved list by `creator`, None if no lists exist
    """
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
