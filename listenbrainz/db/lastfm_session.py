# -*- coding: utf-8 -*-

import binascii
import os
import random
import string
import uuid

from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db.lastfm_user import User


class Session(object):
    """ Session class required by the api-compat """

    def __init__(self, id, user_id, sid, api_key, timestamp):
        self.id = id
        self.sid = sid
        self.api_key = api_key
        self.timestamp = timestamp
        self.user_id = user_id
        self.user = User.load_by_id(user_id)

    @staticmethod
    def load(session_key):
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
                 WHERE sid = :sid
            """), {
                'sid': session_key,
            })
            row = result.fetchone()
            if row:
                return Session(row.id, row.user_id, row.sid, row.api_key, row.ts)
            return None


    @staticmethod
    def generate(user_id, sid, api_key):
        with db.engine.begin() as connection:
            result = connection.execute(text("""
                INSERT INTO api_compat.session (user_id, sid, api_key)
                     VALUES (:user_id, :sid, :api_key)
                  RETURNING id, user_id, sid, api_key, ts
                 """), {
                'user_id': user_id,
                'sid': sid,
                'api_key': api_key
            })
            row = result.fetchone()
            return Session(row.id, row.user_id, row.sid, row.api_key, row.ts)

    @staticmethod
    def create(token):
        """ Create a new session for the user by consuming the token.
            If session already exists for the user then renew the session_key(sid).
        """
        sid = os.urandom(20).hex()
        session = Session.generate(token.user.id, sid, token.api_key)
        token.consume()
        return session



    @staticmethod
    def create_by_user_id(user_id):
        """ Create a new session for the user for the deprecated audioscrobbler API v1.2.
            This only requires a user_id, so we use random values for api_key and other things
        """

        # sids for audioscrobbler v1.2 are of length 32
        sid = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(32))
        api_key = str(uuid.uuid4())
        return Session.generate(user_id, sid, api_key)
