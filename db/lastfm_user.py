# -*- coding: utf-8 -*-
import db
from sqlalchemy import text


class User(object):
    """ User class required by the api-compat """

    def __init__(self, row):
        self.id, self.created, self.name, self.api_key = row

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
            result = connection.execute(text(""" SELECT * FROM "user" WHERE
                                            musicbrainz_id = :mb_id """), {"mb_id": mb_id})
            row = result.fetchone()
            if row:
                return User(row)
            return None

    @staticmethod
    def load_by_id(serial):
        with db.engine.connect() as connection:
            result = connection.execute(text(""" SELECT * FROM "user" WHERE id=:id """), {"id": serial})
            row = result.fetchone()
            if row:
                return User(row)
            return None

    @staticmethod
    def load_by_sessionkey(session_key, api_key):
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT "user".*
                  FROM api_compat.session, "user"
                 WHERE api_key = :api_key AND sid = :sk AND "user".id = session.user_id
            """), {
                "api_key": api_key,
                "sk": session_key
            })
            row = result.fetchone()
            if row:
                return User(row)
            return None

    @staticmethod
    def get_play_count(user_id):
        """ Get playcount from the given user name.
        """
        with db.engine.connect() as connection:
            result = connection.execute(text(""" SELECT COUNT(*) FROM listen WHERE
                                            user_id = :user_id """), {"user_id": user_id})
            return int(result.fetchone()[0])
