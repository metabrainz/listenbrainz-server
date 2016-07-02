"""
This module contains classes required by the compact API.
"""

import os
import binascii
from datetime import datetime, timedelta
from db import db


# Token expiration time in minutes
TOKEN_EXPIRATION_TIME = 60


class User(object):
    def __init__(self, row):
        serial, created, name, auth_token = row
        self.id = serial
        self.name = name
        self.created = created
        self.api_key = auth_token

    @staticmethod
    def get_id(mb_id):
        result = db.session.execute(""" SELECT id FROM "user" WHERE
                                        musicbrainz_id = :mb_id """, {"mb_id": mb_id})
        db.session.commit()
        row = result.fetchone()
        if row:
            return row[0]
        return None

    @staticmethod
    def load_by_name(mb_id):
        result = db.session.execute(""" SELECT * FROM "user" WHERE
                                        musicbrainz_id = :mb_id """, {"mb_id": mb_id})
        db.session.commit()
        row = result.fetchone()
        if row:
            return User(row)
        return None

    @staticmethod
    def load_by_id(serial):
        result = db.session.execute(""" SELECT * FROM "user" WHERE id=:id """, {"id": serial})
        db.session.commit()
        row = result.fetchone()
        if row:
            return User(row)
        return None

    @staticmethod
    def load_by_apikey(api_key):
        result = db.session.execute(""" SELECT * FROM "user" WHERE
                                        auth_token = :auth_token """, {"auth_token": api_key})
        db.session.commit()
        row = result.fetchone()
        if row:
            return User(row)
        return None

    @staticmethod
    def get_play_count(user_id):
        """ Get playcount from the given user name.
        """
        result = db.session.execute(""" SELECT COUNT(*) FROM listen WHERE
                                        user_id = :user_id """, {"user_id": user_id})
        db.session.commit()
        return int(result.fetchone()[0])

class Session(object):
    def __init__(self, row):
        serial, userid, sid, api_key, timestamp = row
        self.id = serial
        self.user = User.load_by_id(userid)
        self.sid = sid
        self.api_key = api_key
        self.timestamp = timestamp

    @staticmethod
    def load(session, api_key=None):
        """ Load the session details from the database.
            If the api_key is also supplied then verify it as well.
        """
        dic = {'sid': session}
        query = "SELECT * FROM session WHERE sid=:sid"
        if api_key:
            dic['api_key'] = api_key
            query = "SELECT * FROM session WHERE sid=:sid AND api_key=:api_key"

        result = db.session.execute(query, dic)
        db.session.commit()
        row = result.fetchone()
        if row:
            return Session(row)
        return None

    @staticmethod
    def create(token):
        """ Create a new session for the user by consuming the token.
            If session already exists for the user then renew the session_key(sid).
        """
        session = binascii.b2a_hex(os.urandom(20))
        db.session.execute("INSERT INTO session (user_id, sid, api_key) VALUES (:user_id, :sid, :api_key) \
                            ON CONFLICT(user_id, api_key) DO UPDATE SET (sid, ts) = (EXCLUDED.sid, EXCLUDED.ts)",
                            {'user_id': token.user.id, 'sid': session, 'api_key': token.api_key})
        db.session.commit()
        token.consume()
        return Session.load(session)


class Token(object):
    def __init__(self, row):
        id, userid, token, api_key, timestamp = row
        self.id = id
        self.token = token
        self.timestamp = timestamp
        self.api_key = api_key
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

        result = db.session.execute(query, dic)
        db.session.commit()
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

        result = db.session.execute(query, params)
        db.session.commit()
        row = result.fetchone()
        if row:
            return Token(row)
        return None

    @staticmethod
    def generate(api_key):
        token = binascii.b2a_hex(os.urandom(20))
        db.session.execute('INSERT INTO token (token, api_key) VALUES (:token, :api_key) \
                            ON CONFLICT(api_key) DO UPDATE SET token = EXCLUDED.token, ts = EXCLUDED.ts',
                           {'token': token, 'api_key': api_key})
        db.session.commit()
        return Token.load(token)

    def has_expired(self):
        """ Check if the token has expired.
        """
        if self.timestamp < datetime.utcnow() - timedelta(minutes=TOKEN_EXPIRATION_TIME):
            return True
        return False

    def approve(self, user):
        """ Authenticate the token.
        """
        db.session.execute("UPDATE token SET user_id = :uid WHERE token=:token",
                           {'uid': User.get_id(user), 'token': self.token})
        db.session.commit()

    def consume(self):
        """ Use token to be able to create a new session.
        """
        db.session.execute("DELETE FROM token WHERE id=:id", {'id': self.id})
        db.session.commit()
