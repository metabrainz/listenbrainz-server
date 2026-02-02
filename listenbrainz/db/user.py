import logging
from typing import Optional

import sqlalchemy
import uuid

from datetime import datetime

from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException
from typing import Tuple, List

from flask import current_app, render_template
from brainzutils.mail import send_mail


logger = logging.getLogger(__name__)


def create(db_conn, musicbrainz_row_id: int, musicbrainz_id: str, email: str = None) -> int:
    """Create a new user.

    Args:
        db_conn: database connection
        musicbrainz_row_id (int): the MusicBrainz row ID of the user
        musicbrainz_id (str): MusicBrainz username of a user.
        email (str): email of the user

    Returns:
        ID of newly created user.
    """
    result = db_conn.execute(text("""
        INSERT INTO "user" (musicbrainz_id, musicbrainz_row_id, auth_token, email)
             VALUES (:mb_id, :mb_row_id, :token, :email)
          RETURNING id
    """), {
        "mb_id": musicbrainz_id,
        "token": str(uuid.uuid4()),
        "mb_row_id": musicbrainz_row_id,
        "email": email,
    })
    db_conn.commit()
    return result.fetchone().id


def update_token(db_conn, id):
    """Update a user's token to a new UUID

    Args:
        db_conn: database connection
        id (int) - the row id of the user to update
    """
    try:
        db_conn.execute(sqlalchemy.text("""
            UPDATE "user"
               SET auth_token = :token
             WHERE id = :id
        """), {
            "token": str(uuid.uuid4()),
            "id": id
        })
        db_conn.commit()
    except DatabaseException as e:
        logger.error(e)
        raise


USER_GET_COLUMNS = ['id', 'created', 'musicbrainz_id', 'auth_token',
                    'last_login', 'latest_import', 'gdpr_agreed', 'musicbrainz_row_id', 'login_id', 'is_paused']


def get(db_conn, id: int, *, fetch_email: bool = False):
    """Get user with a specified ID.

    Args:
        db_conn: database connection
        id: ID of a user.
        fetch_email: whether to return email in response

    Returns:
        Dictionary with the following structure:
        {
            "id": <listenbrainz user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
            "auth_token": <authentication token>,
            "last_login": <date that this user last logged in>,
            "latest_import": <date that this user last performed a data import>
            "gdpr_agreed": <boolean, if the user has agreed to terms and conditions>,
            "musicbrainz_row_id": <musicbrainz row id associated with this user>,
            "login_id": <token used for login sessions>
            "is_paused": <boolean, if the user is paused>
        }
    """
    columns = USER_GET_COLUMNS + ['email'] if fetch_email else USER_GET_COLUMNS
    result = db_conn.execute(sqlalchemy.text("""
        SELECT {columns}
          FROM "user"
         WHERE id = :id
    """.format(columns=','.join(columns))), {"id": id})
    return result.mappings().first()


def get_by_login_id(db_conn, login_id):
    """Get user with a specified login ID.

    Args:
        db_conn: database connection
        id (UUID): login ID of a user.

    Returns:
        Dictionary with the following structure:
        {
            "id": <listenbrainz user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
            "auth_token": <authentication token>,
            "last_login": <date that this user last logged in>,
            "latest_import": <date that this user last performed a data import>
            "gdpr_agreed": <boolean, if the user has agreed to terms and conditions>,
            "musicbrainz_row_id": <musicbrainz row id associated with this user>,
            "login_id": <token used for login sessions>
            "is_paused": <boolean, if the user is paused>
        }
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT {columns}
          FROM "user"
         WHERE login_id = :user_login_id
    """.format(columns=','.join(USER_GET_COLUMNS))), {"user_login_id": login_id})
    return result.mappings().first()


def get_many_users_by_mb_id(db_conn, musicbrainz_ids: List[str]):
    """Load a list of users given their musicbrainz login name

    Args:
        db_conn: database connection object
        musicbrainz_ids: A list of musicbrainz usernames

    Returns:
        A dictionary where keys are the username, and values are dictionaries of user information
        following the same format as `get_by_mb_id`.
        If a provided username doesn't exist, it won't be returned.
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT {columns}
          FROM "user"
         WHERE LOWER(musicbrainz_id) in :mb_ids
    """.format(columns=','.join(USER_GET_COLUMNS))),
                                {"mb_ids": tuple([mbname.lower() for mbname in musicbrainz_ids])})
    return {row["musicbrainz_id"].lower(): row for row in result.mappings()}


def get_by_mb_id(db_conn, musicbrainz_id, *, fetch_email: bool = False):
    """Get user with a specified MusicBrainz ID.

    Args:
        db_conn: database connection
        musicbrainz_id (str): MusicBrainz username of a user.
        fetch_email: whether to return email in response

    Returns:
        Dictionary with the following structure:
        {
            "id": <listenbrainz user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
            "auth_token": <authentication token>,
            "last_login": <date that this user last logged in>,
            "latest_import": <date that this user last performed a data import>
            "gdpr_agreed": <boolean, if the user has agreed to terms and conditions>,
            "musicbrainz_row_id": <musicbrainz row id associated with this user>,
            "login_id": <token used for login sessions>
            "is_paused": <boolean, if the user is paused>
        }
    """
    columns = USER_GET_COLUMNS + ['email'] if fetch_email else USER_GET_COLUMNS
    result = db_conn.execute(sqlalchemy.text("""
        SELECT {columns}
          FROM "user"
         WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)
    """.format(columns=','.join(columns))), {"mb_id": musicbrainz_id})
    return result.mappings().first()


def get_by_token(db_conn, token: str, *, fetch_email: bool = False):
    """Get user with a specified authentication token.

    Args:
        db_conn: database connection object
        token: Authentication token associated with user's account.
        fetch_email: whether to return email in response

    Returns:
        Dictionary with the following structure:
        {
            "id": <user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
        }
    """
    columns = USER_GET_COLUMNS + ['email'] if fetch_email else USER_GET_COLUMNS
    result = db_conn.execute(sqlalchemy.text("""
        SELECT {columns}
          FROM "user"
         WHERE auth_token = :auth_token
    """.format(columns=','.join(columns))), {"auth_token": token})
    return result.mappings().first()


def get_user_count(db_conn):
    """ Get total number of users in database.

    Returns:
        int: user count
    """
    try:
        result = db_conn.execute(sqlalchemy.text("""
            SELECT count(*) AS user_count
              FROM "user"
        """))
        row = result.fetchone()
        return row.user_count
    except DatabaseException as e:
        logger.error(e)
        raise


def get_or_create(db_conn, musicbrainz_row_id: int, musicbrainz_id: str) -> dict:
    """Get user with a specified MusicBrainz ID, or create if there's no account.

    Args:
        db_conn: database connection
        musicbrainz_row_id (int): the MusicBrainz row ID of the user
        musicbrainz_id (str): MusicBrainz username of a user.

    Returns:
        Dictionary with the following structure:
        {
            "id": <user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
            "auth_token": <authentication token>,
        }
    """
    user = get_by_mb_row_id(db_conn, musicbrainz_row_id, musicbrainz_id=musicbrainz_id)
    if not user:
        create(db_conn, musicbrainz_row_id, musicbrainz_id)
        user = get_by_mb_row_id(db_conn, musicbrainz_row_id)
    return user


def update_last_login(db_conn, musicbrainz_id):
    """ Update the value of last_login field for user with specified MusicBrainz ID

    Args:
        db_conn: database connection
        musicbrainz_id (str): MusicBrainz username of a user
    """
    try:
        db_conn.execute(sqlalchemy.text("""
            UPDATE "user"
               SET last_login = NOW()
             WHERE musicbrainz_id = :musicbrainz_id
            """), {
            "musicbrainz_id": musicbrainz_id,
        })
        db_conn.commit()
    except sqlalchemy.exc.ProgrammingError as err:
        logger.error(err)
        raise DatabaseException("Couldn't update last_login: %s" % str(err))


def get_all_users(db_conn, created_before=None, columns=None):
    """ Returns a list of all users in the database

        Args:
            db_conn: database connection
            columns: a list of columns to be returned for each user
            created_before (datetime): only return users who were created before this timestamp, defaults to now

        Returns: if columns is None, A list of dicts of the following format for each user
            {
                'id': int
                'musicbrainz_id': string
                'created': datetime.datetime
                'auth_token': uuid
                'last_login': datetime.datetime
                'latest_import': datetime.datetime
            }

            otherwise, a list of dicts for each user with only the columns passed as argument
    """

    if columns is None:
        columns = USER_GET_COLUMNS

    if created_before is None:
        created_before = datetime.now()

    result = db_conn.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM "user"
             WHERE created <= :created
          ORDER BY id
        """.format(columns=', '.join(columns))), {
        "created": created_before,
    })

    return result.mappings().all()


def delete(db_conn, id):
    """ Delete the user with specified row ID from the database.

    Note: this deletes all statistics and api_compat sessions and tokens
    associated with the user also.

    Args:
        db_conn: database connection
        id (int): the row ID of the listenbrainz user
    """
    try:
        db_conn.execute(sqlalchemy.text("""
            DELETE FROM "user"
                  WHERE id = :id
            """), {
            'id': id,
        })
        db_conn.commit()
    except sqlalchemy.exc.ProgrammingError as err:
        logger.error(err)
        raise DatabaseException("Couldn't delete user: %s" % str(err))


def agree_to_gdpr(db_conn, musicbrainz_id):
    """ Update the gdpr_agreed column for user with specified MusicBrainz ID with current time.

    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user
    """
    try:
        db_conn.execute(sqlalchemy.text("""
            UPDATE "user"
               SET gdpr_agreed = NOW()
             WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)
            """), {
            'mb_id': musicbrainz_id,
        })
        db_conn.commit()
    except sqlalchemy.exc.ProgrammingError as err:
        logger.error(err)
        raise DatabaseException(
            "Couldn't update gdpr agreement for user: %s" % str(err))


def get_by_mb_row_id(db_conn, musicbrainz_row_id, musicbrainz_id=None):
    """ Get user with specified MusicBrainz row id.

    Note: this function also optionally takes a MusicBrainz username to fall back on
    if no user with specified MusicBrainz row ID is found.

     Args:
        db_conn: database connection
        musicbrainz_row_id (int): the MusicBrainz row ID of the user
        musicbrainz_id (str): the MusicBrainz username of the user

    Returns: a dict representing the user if found, else None.
    """
    filter_str = ''
    filter_data = {}
    if musicbrainz_id:
        filter_str = 'OR LOWER(musicbrainz_id) = LOWER(:musicbrainz_id) AND musicbrainz_row_id IS NULL'
        filter_data['musicbrainz_id'] = musicbrainz_id

    filter_data['musicbrainz_row_id'] = musicbrainz_row_id

    result = db_conn.execute(sqlalchemy.text("""
        SELECT {columns}
          FROM "user"
         WHERE musicbrainz_row_id = :musicbrainz_row_id
         {optional_filter}
    """.format(columns=','.join(USER_GET_COLUMNS), optional_filter=filter_str)), filter_data)

    return result.mappings().first()


def get_similar_users(db_conn, user_id: int) -> Optional[list[dict]]:
    """ Given a user_id, fetch the similar users for that given user ordered by "similarity" score.

        :code:: python
        ```
        [   
            { 
                "musicbrainz_id" : "user_x",
                "id": 123, 
                "similarity": 0.54 
            },
            { 
                "musicbrainz_id" : "user_y",
                "id": 545, 
                "similarity": 0.22 
            }
        ]
        ```
            
        :param user_id: ID of the user.
        :type user_id: ``int``
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT musicbrainz_id
             , id
             , value AS similarity -- first element of array is local similarity, second is global_similarity
          FROM recommendation.similar_user r 
          JOIN jsonb_each(r.similar_users) j
            ON TRUE
          JOIN "user" u
            ON j.key::int = u.id 
         WHERE user_id = :user_id
         ORDER BY similarity DESC
    """), {"user_id": user_id})
    return [dict(**row) for row in result.mappings()]


def get_users_by_id(db_conn, user_ids: List[int]):
    """ Given a list of user ids, fetch one ore more users at the same time.
        Returns a dict mapping user_ids to user_names. """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT id, musicbrainz_id
          FROM "user"
         WHERE id IN :user_ids
    """), {
        'user_ids': tuple(user_ids)
    })
    row_id_username_map = {}
    for row in result.fetchall():
        row_id_username_map[row.id] = row.musicbrainz_id
    return row_id_username_map


def is_user_reported(db_conn, reporter_id: int, reported_id: int):
    """ Check whether the user identified by reporter_id has reported the
    user identified by reported_id"""
    result = db_conn.execute(sqlalchemy.text("""
        SELECT *
          FROM reported_users
         WHERE reporter_user_id = :reporter_id
           AND reported_user_id = :reported_id
    """), {
        "reporter_id": reporter_id,
        "reported_id": reported_id
    })
    return True if result.fetchone() else False


def report_user(db_conn, reporter_id: int, reported_id: int, reason: str = None):
    """ Create a report from user with reporter_id against user with
     reported_id"""
    db_conn.execute(sqlalchemy.text("""
        INSERT INTO reported_users (reporter_user_id, reported_user_id, reason)
             VALUES (:reporter_id, :reported_id, :reason)
             ON CONFLICT DO NOTHING
            """), {
        "reporter_id": reporter_id,
        "reported_id": reported_id,
        "reason": reason,
    })
    db_conn.commit()


def update_user_details(db_conn, lb_id: int, musicbrainz_id: str, email: str):
    """ Update the email field and MusicBrainz ID of the user specified by the lb_id

    Args:
        lb_id: listenbrainz row id of the user
        musicbrainz_id: MusicBrainz username of a user
        email: email of a user
    """
    try:
        db_conn.execute(sqlalchemy.text("""
            UPDATE "user"
               SET email = :email
                 , musicbrainz_id = :musicbrainz_id
             WHERE id = :lb_id
            """), {
            "lb_id": lb_id,
            "musicbrainz_id": musicbrainz_id,
            "email": email
        })
        db_conn.commit()
    except sqlalchemy.exc.ProgrammingError as err:
        logger.error(err)
        raise DatabaseException("Couldn't update user's email: %s" % str(err))


def search_query(db_conn, search_term: str, limit: int):
    result = db_conn.execute(sqlalchemy.text("""
            SELECT musicbrainz_id, similarity(musicbrainz_id, :search_term) AS query_similarity
              FROM "user"
             WHERE musicbrainz_id <% :search_term
          ORDER BY query_similarity DESC
             LIMIT :limit
            """), {
        "search_term": search_term,
        "limit": limit
    })
    rows = result.fetchall()
    return rows


def search(db_conn, search_term: str, limit: int, searcher_id: int = None) -> List[Tuple[str, float, float]]:
    """ Searches for the input term in the database and returns list of potential user matches along with
    their similarity to the searcher if available.

    Args:
        db_conn: database connection
        search_term: the term to search in username column
        limit: max number of search results to fetch
        searcher_id: the user_id of the user who did the search
    Returns:
          tuple of form (musicbrainz_id, query_similarity, user_similarity) where
          musicbrainz_id: username of user returned in search result
          query_similarity: the similarity between the query term and the returned username
          user_similarity: the similarity between the user and the searcher as in similar users
          calculated by spark
    """
    rows = search_query(db_conn, search_term, limit)
    if not rows:
        return []

    search_results = []

    if searcher_id:
        # Constructing an id-similarity map
        similar_users = get_similar_users(db_conn, searcher_id)
        id_similarity_map = {user["musicbrainz_id"]: user["similarity"] for user in similar_users}
        for row in rows:
            similarity = id_similarity_map.get(row.musicbrainz_id, None)
            search_results.append((row.musicbrainz_id, row.query_similarity, similarity))
    else:
        search_results = [(row.musicbrainz_id, row.query_similarity, None) for row in rows]
    return search_results


def search_user_name(db_conn, search_term: str, limit: int) -> List[object]:
    rows = search_query(db_conn, search_term, limit)

    if not rows:
        return []

    search_results = []

    for row in rows:
        search_results.append({"user_name": row.musicbrainz_id})
    return search_results


def get_all_usernames():
    """ Return a map of all user ids to their musicbrainz usernames """
    user_id_map = {}
    query = 'SELECT id, musicbrainz_id FROM "user"'
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query))
        for row in result:
            user_id_map[row.id] = row.musicbrainz_id
    return user_id_map


def pause(db_conn,id):
    """ Sets the user's is_paused flag to true
    with specified row ID from the database.
    
    Args:
        db_conn: database connection
        id (int): the row ID of the listenbrainz user
    """
    try:
        db_conn.execute(sqlalchemy.text("""
            UPDATE "user"
               SET is_paused = true
             WHERE id = :id
            """), {
            'id': id,
        })
        db_conn.commit()
        _notify_user_paused(db_conn,id,True)

    except sqlalchemy.exc.ProgrammingError as err:
        logger.error(err)
        raise DatabaseException("Couldn't pause user: %s" % str(err))


def unpause(db_conn,id):
    """ Sets the user's is_paused flag to false
    with specified row ID from the database.
    
    Args:
        db_conn: database connection
        id (int): the row ID of the listenbrainz user
    """
    try:
        db_conn.execute(sqlalchemy.text("""
            UPDATE "user"
               SET is_paused = false
             WHERE id = :id
            """), {
            'id': id,
        })
        db_conn.commit()
        _notify_user_paused(db_conn,id,False)

    except sqlalchemy.exc.ProgrammingError as err:
        logger.error(err)
        raise DatabaseException("Couldn't unpause user: %s" % str(err))


def _notify_user_paused(db_conn, user_id,paused):
    user = get(db_conn, user_id, fetch_email=True)
    if user["email"] is None:
        logger.error("%s's email not found" % user["musicbrainz_id"])
        return
    url = 'https://metabrainz.org/contact'
    template = 'emails/id_paused.txt' if paused else 'emails/id_unpaused.txt'
    subject = ("Your ListenBrainz account %s has been paused and is not accepting incoming listens" % user["musicbrainz_id"] if paused
                 else "Your ListenBrainz account %s has been unpaused and is accepting incoming listens" % user["musicbrainz_id"])
    content = render_template(template, username=user["musicbrainz_id"], url=url)
    send_mail(
        subject=subject,
        text=content,
        recipients=[user["email"]],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )
