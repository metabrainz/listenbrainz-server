# -*- coding: utf-8 -*-
import os
import binascii
import db
from sqlalchemy import text
from lastfm_user import User


class Session(object):
    """ Session class required by the api-compat """

    def __init__(self, id, userid, sid, api_key, timestamp):
        self.id = id
        self.sid = sid
        self.api_key = api_key
        self.timestamp = timestamp
        self.user = User.load_by_id(userid)

    @staticmethod
    def load(session_key, api_key):
        """ Load the session details from the database.
            API_key and Session_key are required for a session.
        """
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT id
                     , user_id
                     , sid
                     , api_key
                     , ts
                  FROM api_compat.session
                 WHERE sid=:sid AND api_key=:api_key
            """), {
                'sid': session_key,
                'api_key': api_key
            })
            row = result.fetchone()
            if row:
                id, userid, sid, api_key, timestamp = row
                return Session(id, userid, sid, api_key, timestamp)
            return None

    @staticmethod
    def create(token):
        """ Create a new session for the user by consuming the token.
            If session already exists for the user then renew the session_key(sid).
        """
        session = binascii.b2a_hex(os.urandom(20))
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                INSERT INTO api_compat.session (user_id, sid, api_key)
                     VALUES (:user_id, :sid, :api_key)
                  RETURNING id, user_id, sid, api_key, ts
                 """), {
                'user_id': token.user.id,
                'sid': session,
                'api_key': token.api_key
            })
            token.consume()
            id, user_id, sid, api_key, ts, = result.fetchone()
            return Session(id, user_id, sid, api_key, ts)
