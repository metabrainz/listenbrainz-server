# -*- coding: utf-8 -*-
import os
import binascii
from datetime import datetime, timedelta
import db
from sqlalchemy import text
from lastfm_user import User

# Token expiration time in minutes
TOKEN_EXPIRATION_TIME = 60


class Token(object):
    """ Token class required by the api-compat """

    def __init__(self, row):
        self.id, userid, self.token, self.api_key, self.timestamp = row
        self.user = User.load_by_id(userid)

    @staticmethod
    def is_valid_api_key(api_key, user_id=None):
        """ Check if the api_key is valid or not, and return a boolean.
        """
        dic = {"api_key": api_key}
        if user_id:
            query = 'SELECT * FROM "user" WHERE auth_token=:api_key AND musicbrainz_id=:user_id'
            dic['user_id'] = user_id
        else:
            query = 'SELECT * FROM "user" WHERE auth_token=:api_key'

        with db.engine.connect() as connection:
            result = connection.execute(text(query), dic)
            if result.fetchone():
                return True
            return False

    @staticmethod
    def load(token, api_key=None):
        """ Load the token from database. Check api_key as well if present.
        """
        query = "SELECT * FROM token WHERE token=:token"
        params = {'token': token}
        if api_key:
            query = "SELECT * FROM token WHERE token=:token AND api_key=:api_key"
            params['api_key'] = api_key

        with db.engine.connect() as connection:
            result = connection.execute(text(query), params)
            row = result.fetchone()
            if row:
                return Token(row)
            return None

    @staticmethod
    def generate(api_key):
        token = binascii.b2a_hex(os.urandom(20))
        with db.engine.connect() as connection:
            q = """ INSERT INTO token (token, api_key) VALUES (:token, :api_key)
                    ON CONFLICT(api_key) DO UPDATE SET token = EXCLUDED.token, ts = EXCLUDED.ts
                """
            connection.execute(text(q), {'token': token, 'api_key': api_key})
        return Token.load(token)

    def has_expired(self):
        """ Check if the token has expired.
            NOTE: Make sure you capture timezones to avoid issues.
        """
        return (self.timestamp < datetime.now() - timedelta(minutes=TOKEN_EXPIRATION_TIME))

    def approve(self, user):
        """ Authenticate the token. User has to be present.
        """
        with db.engine.connect() as connection:
            connection.execute(text("UPDATE token SET user_id = :uid WHERE token=:token"),
                               {'uid': User.get_id(user), 'token': self.token})
        self.user = User.load_by_name(user)

    def consume(self):
        """ Use token to be able to create a new session.
        """
        with db.engine.connect() as connection:
            connection.execute(text("DELETE FROM token WHERE id=:id"), {'id': self.id})
