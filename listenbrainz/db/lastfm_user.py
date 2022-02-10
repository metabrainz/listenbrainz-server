# -*- coding: utf-8 -*-

from sqlalchemy import text

from listenbrainz import db


class User(object):
    """ User class required by the api-compat """

    def __init__(self, id, created, name, api_key):
        self.id = id
        self.created = created
        self.name = name
        self.api_key = api_key

    @staticmethod
    def get_id(mb_id):
        with db.engine.connect() as connection:
            result = connection.execute(text(""" SELECT id FROM "user" WHERE
                                            musicbrainz_id = :mb_id """), {"mb_id": mb_id})
            row = result.fetchone()
            if row:
                return row[0]
            return None

    @staticmethod
    def load_by_name(mb_id):
        with db.engine.connect() as connection:
            result = connection.execute(text(""" SELECT id, created, musicbrainz_id, auth_token \
                                                   FROM "user" \
                                                  WHERE musicbrainz_id = :mb_id """), {"mb_id": mb_id})
            row = result.fetchone()
            if row:
                return User(row['id'], row['created'], row['musicbrainz_id'], row['auth_token'])
            return None

    @staticmethod
    def load_by_id(serial):
        with db.engine.connect() as connection:
            result = connection.execute(text(""" SELECT id, created, musicbrainz_id, auth_token \
                                                   FROM "user"
                                                  WHERE id=:id """), {"id": serial})
            row = result.fetchone()
            if row:
                return User(row['id'], row['created'], row['musicbrainz_id'], row['auth_token'])
            return None

    @staticmethod
    def load_by_sessionkey(session_key, api_key):
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT "user".id
                     , "user".created
                     , "user".musicbrainz_id
                     , "user".auth_token
                  FROM api_compat.session, "user"
                 WHERE api_key = :api_key AND sid = :sk AND "user".id = session.user_id
            """), {
                "api_key": api_key,
                "sk": session_key
            })
            row = result.fetchone()
            if row:
                return User(row['id'], row['created'], row['musicbrainz_id'], row['auth_token'])
            return None

    @staticmethod
    def get_play_count(user_id, listenstore):
        """ Get playcount from the given user name.
        """
        user = User.load_by_id(user_id)
        return listenstore.get_listen_count_for_user(user.id)
