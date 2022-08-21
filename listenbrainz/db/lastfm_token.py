# -*- coding: utf-8 -*-

import binascii
import os
from datetime import datetime, timedelta

from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db.lastfm_user import User

# Token expiration time in minutes
TOKEN_EXPIRATION_TIME = 60


class Token(object):
    """ Token class required by the api-compat """

    def __init__(self, id, userid, token, api_key, ts):
        self.id = id
        self.token = token
        self.api_key = api_key
        self.timestamp = ts
        self.user = User.load_by_id(userid)

    @staticmethod
    def is_valid_api_key(api_key, user_id=None):
        """ Check if the api_key is valid or not, and return a boolean.

            Last.fm uses a (api_key, user) mapping to detect the app which is making
            the request, but since this mapping is private we have no way to authenticate
            the api_key.

            To prevent the abuse of the service, it falls back to ratelimiter.
        """
        return True

    @staticmethod
    def load(token, api_key=None):
        """ Load the token from database. Check api_key as well if present.
        """
        query = """SELECT id, user_id, token, api_key, ts
                     FROM api_compat.token
                    WHERE token = :token"""
        params = {'token': token}
        if api_key:
            query = """SELECT id, user_id, token, api_key, ts
                         FROM api_compat.token
                        WHERE token = :token
                          AND api_key = :api_key"""
            params['api_key'] = api_key

        with db.engine.begin() as connection:
            result = connection.execute(text(query), params)
            row = result.fetchone()
            if row:
                return Token(row.id, row.user_id, row.token, row.api_key, row.ts)
            return None

    @staticmethod
    def generate(api_key):
        token = os.urandom(20).hex()
        with db.engine.begin() as connection:
            q = """ INSERT INTO api_compat.token (token, api_key) VALUES (:token, :api_key)
                    ON CONFLICT(api_key) DO UPDATE SET token = EXCLUDED.token, ts = EXCLUDED.ts
                """
            connection.execute(text(q), {'token': token, 'api_key': api_key})
        return Token.load(token)

    def has_expired(self):
        """ Check if the token has expired.
            NOTE: Make sure you capture timezones to avoid issues.
        """
        return self.timestamp < datetime.now() - timedelta(minutes=TOKEN_EXPIRATION_TIME)

    def approve(self, user):
        """ Authenticate the token. User has to be present.
        """
        with db.engine.begin() as connection:
            connection.execute(text("UPDATE api_compat.token SET user_id = :uid WHERE token=:token"),
                               {'uid': User.get_id(user), 'token': self.token})
        self.user = User.load_by_name(user)

    def consume(self):
        """ Use token to be able to create a new session.
        """
        with db.engine.begin() as connection:
            connection.execute(text("DELETE FROM api_compat.token WHERE id=:id"), {'id': self.id})
