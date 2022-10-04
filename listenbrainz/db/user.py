import logging
from typing import Optional

import sqlalchemy
import uuid

from datetime import datetime
from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException
from data.model.similar_user_model import SimilarUsers
from typing import Tuple, List


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create(musicbrainz_row_id: int, musicbrainz_id: str, email: str = None) -> int:
    """Create a new user.

    Args:
        musicbrainz_row_id (int): the MusicBrainz row ID of the user
        musicbrainz_id (str): MusicBrainz username of a user.
        email (str): email of the user

    Returns:
        ID of newly created user.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO "user" (musicbrainz_id, musicbrainz_row_id, auth_token, email)
                 VALUES (:mb_id, :mb_row_id, :token, :email)
              RETURNING id
        """), {
            "mb_id": musicbrainz_id,
            "token": str(uuid.uuid4()),
            "mb_row_id": musicbrainz_row_id,
            "email": email,
        })

        return result.fetchone().id


def update_token(id):
    """Update a user's token to a new UUID

    Args:
        id (int) - the row id of the user to update
    """
    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET auth_token = :token
                 WHERE id = :id
            """), {
                "token": str(uuid.uuid4()),
                "id": id
            })
        except DatabaseException as e:
            logger.error(e)
            raise


USER_GET_COLUMNS = ['id', 'created', 'musicbrainz_id', 'auth_token',
                    'last_login', 'latest_import', 'gdpr_agreed', 'musicbrainz_row_id', 'login_id']


def get(id: int, *, fetch_email: bool = False):
    """Get user with a specified ID.

    Args:
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
        }
    """
    columns = USER_GET_COLUMNS + ['email'] if fetch_email else USER_GET_COLUMNS
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM "user"
             WHERE id = :id
        """.format(columns=','.join(columns))), {"id": id})
        return result.mappings().first()


def get_by_login_id(login_id):
    """Get user with a specified login ID.

    Args:
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
        }
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM "user"
             WHERE login_id = :user_login_id
        """.format(columns=','.join(USER_GET_COLUMNS))), {"user_login_id": login_id})
        return result.mappings().first()


def get_many_users_by_mb_id(musicbrainz_ids: List[str]):
    """Load a list of users given their musicbrainz login name

    Args:
        musicbrainz_ids: A list of musicbrainz usernames

    Returns:
        A dictionary where keys are the username, and values are dictionaries of user information
        following the same format as `get_by_mb_id`.
        If a provided username doesn't exist, it won't be returned.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM "user"
             WHERE LOWER(musicbrainz_id) in :mb_ids
        """.format(columns=','.join(USER_GET_COLUMNS))), {"mb_ids": tuple([mbname.lower() for mbname in musicbrainz_ids])})
        return {row["musicbrainz_id"].lower(): row for row in result.mappings()}


def get_by_mb_id(musicbrainz_id, *, fetch_email: bool = False):
    """Get user with a specified MusicBrainz ID.

    Args:
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
        }
    """
    columns = USER_GET_COLUMNS + ['email'] if fetch_email else USER_GET_COLUMNS
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM "user"
             WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)
        """.format(columns=','.join(columns))), {"mb_id": musicbrainz_id})
        return result.mappings().first()


def get_by_token(token: str, *, fetch_email: bool = False):
    """Get user with a specified authentication token.

    Args:
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
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM "user"
             WHERE auth_token = :auth_token
        """.format(columns=','.join(columns))), {"auth_token": token})
        return result.mappings().first()


def get_user_count():
    """ Get total number of users in database.

    Returns:
        int: user count
    """

    with db.engine.connect() as connection:
        try:
            result = connection.execute(sqlalchemy.text("""
                SELECT count(*) AS user_count
                  FROM "user"
            """))
            row = result.fetchone()
            return row.user_count
        except DatabaseException as e:
            logger.error(e)
            raise


def get_or_create(musicbrainz_row_id: int, musicbrainz_id: str) -> dict:
    """Get user with a specified MusicBrainz ID, or create if there's no account.

    Args:
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
    user = get_by_mb_row_id(musicbrainz_row_id, musicbrainz_id=musicbrainz_id)
    if not user:
        create(musicbrainz_row_id, musicbrainz_id)
        user = get_by_mb_row_id(musicbrainz_row_id)
    return user


def update_last_login(musicbrainz_id):
    """ Update the value of last_login field for user with specified MusicBrainz ID

    Args:
        musicbrainz_id (str): MusicBrainz username of a user
    """

    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET last_login = NOW()
                 WHERE musicbrainz_id = :musicbrainz_id
                """), {
                "musicbrainz_id": musicbrainz_id,
            })
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException(
                "Couldn't update last_login: %s" % str(err))


def get_all_users(created_before=None, columns=None):
    """ Returns a list of all users in the database

        Args:
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

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                SELECT {columns}
                  FROM "user"
                 WHERE created <= :created
              ORDER BY id
            """.format(columns=', '.join(columns))), {
            "created": created_before,
        })

        return result.mappings().all()


def delete(id):
    """ Delete the user with specified row ID from the database.

    Note: this deletes all statistics and api_compat sessions and tokens
    associated with the user also.

    Args:
        id (int): the row ID of the listenbrainz user
    """
    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                DELETE FROM "user"
                      WHERE id = :id
                """), {
                'id': id,
            })
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException("Couldn't delete user: %s" % str(err))


def agree_to_gdpr(musicbrainz_id):
    """ Update the gdpr_agreed column for user with specified MusicBrainz ID with current time.

    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user
    """
    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET gdpr_agreed = NOW()
                 WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)
                """), {
                'mb_id': musicbrainz_id,
            })
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException(
                "Couldn't update gdpr agreement for user: %s" % str(err))


def update_musicbrainz_row_id(musicbrainz_id, musicbrainz_row_id):
    """ Update the musicbrainz_row_id column for user with specified MusicBrainz username.

    Args:
        musicbrainz_id (str): the MusicBrainz ID (username) of the user
        musicbrainz_row_id (int): the MusicBrainz row ID of the user
    """
    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET musicbrainz_row_id = :musicbrainz_row_id
                 WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)
                """), {
                'musicbrainz_row_id': musicbrainz_row_id,
                'mb_id': musicbrainz_id,
            })
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException(
                "Couldn't update musicbrainz row id for user: %s" % str(err))


def get_by_mb_row_id(musicbrainz_row_id, musicbrainz_id=None):
    """ Get user with specified MusicBrainz row id.

    Note: this function also optionally takes a MusicBrainz username to fall back on
    if no user with specified MusicBrainz row ID is found.

     Args:
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
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT {columns}
              FROM "user"
             WHERE musicbrainz_row_id = :musicbrainz_row_id
             {optional_filter}
        """.format(columns=','.join(USER_GET_COLUMNS), optional_filter=filter_str)), filter_data)

        return result.mappings().first()


def validate_usernames(musicbrainz_ids):
    """ Check existence of users in the database and return those users which exist in order.

    Args:
        musicbrainz_ids ([str]): a list of usernames

    Returns: list of users who exist in the database
    """
    with db.engine.connect() as connection:
        r = connection.execute(sqlalchemy.text("""
            SELECT t.musicbrainz_id as musicbrainz_id, id
              FROM "user" u
        RIGHT JOIN unnest(:musicbrainz_ids ::text[]) WITH ORDINALITY t(musicbrainz_id, ord)
                ON LOWER(u.musicbrainz_id) = t.musicbrainz_id
          ORDER BY t.ord
        """), {
            'musicbrainz_ids': [musicbrainz_id.lower() for musicbrainz_id in musicbrainz_ids],
        })
        return [row for row in r.mappings().all() if row["id"] is not None]


def get_users_in_order(user_ids):
    with db.engine.connect() as connection:
        r = connection.execute(sqlalchemy.text("""
            SELECT t.user_id as id, musicbrainz_id
              FROM "user" u
        RIGHT JOIN unnest(:user_ids ::int[]) WITH ORDINALITY t(user_id, ord)
                ON u.id = t.user_id
          ORDER BY t.ord
        """), {
            'user_ids': user_ids,
        })
        return [row for row in r.mappings() if row["musicbrainz_id"] is not None]


def get_similar_users(user_id: int) -> Optional[SimilarUsers]:
    """ Given a user_id, fetch the similar users for that given user.
        Returns a dict { "user_x" : .453, "user_y": .123 } """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT musicbrainz_id AS user_name
                 , value->0 AS similarity -- first element of array is local similarity, second is global_similarity
              FROM recommendation.similar_user r 
              JOIN jsonb_each(r.similar_users) j
                ON TRUE
              JOIN "user" u
                ON j.key::int = u.id 
             WHERE user_id = :user_id
        """), {"user_id": user_id})
        users = {row.user_name: row.similarity for row in result.fetchall()}
        return SimilarUsers(user_id=user_id, similar_users=users)


def get_users_by_id(user_ids: List[int]):
    """ Given a list of user ids, fetch one ore more users at the same time.
        Returns a dict mapping user_ids to user_names. """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
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


def is_user_reported(reporter_id: int, reported_id: int):
    """ Check whether the user identified by reporter_id has reported the
    user identified by reported_id"""
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT *
              FROM reported_users
             WHERE reporter_user_id = :reporter_id
               AND reported_user_id = :reported_id
        """), {
            "reporter_id": reporter_id,
            "reported_id": reported_id
        })
        return True if result.fetchone() else False


def report_user(reporter_id: int, reported_id: int, reason: str = None):
    """ Create a report from user with reporter_id against user with
     reported_id"""
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO reported_users (reporter_user_id, reported_user_id, reason)
                 VALUES (:reporter_id, :reported_id, :reason)
                 ON CONFLICT DO NOTHING
                """), {
            "reporter_id": reporter_id,
            "reported_id": reported_id,
            "reason": reason,
        })


def update_user_details(lb_id: int, musicbrainz_id: str, email: str):
    """ Update the email field and MusicBrainz ID of the user specified by the lb_id

    Args:
        lb_id: listenbrainz row id of the user
        musicbrainz_id: MusicBrainz username of a user
        email: email of a user
    """

    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET email = :email
                     , musicbrainz_id = :musicbrainz_id
                 WHERE id = :lb_id
                """), {
                "lb_id": lb_id,
                "musicbrainz_id": musicbrainz_id,
                "email": email
            })
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException(
                "Couldn't update user's email: %s" % str(err))


def search(search_term: str, limit: int, searcher_id: int = None) -> List[Tuple[str, float, float]]:
    """ Searches for the input term in the database and returns list of potential user matches along with
    their similarity to the searcher if available.

    Args:
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
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
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
        if not rows:
            return []
        similar_users = get_similar_users(searcher_id) if searcher_id else None

        search_results = []
        if similar_users:
            for row in rows:
                similarity = similar_users.similar_users.get(row.musicbrainz_id, None)
                search_results.append((row.musicbrainz_id, row.query_similarity, similarity))
        else:
            search_results = [(row.musicbrainz_id, row.query_similarity, None) for row in rows]
        return search_results
