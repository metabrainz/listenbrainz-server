# -*- coding: utf-8 -*-
import os
import binascii
import db
from sqlalchemy import text
from lastfm_user import User


class Session(object):
    """ Session class required by the api-compat """

    def __init__(self, row):
        self.id, userid, self.sid, self.api_key, self.timestamp = row
        self.user = User.load_by_id(userid)

    @staticmethod
    def load(session, api_key=None):
        """ Load the session details from the database.
            If the api_key is also supplied then verify it as well.
        """
        params = {'sid': session}
        query = "SELECT * FROM session WHERE sid=:sid"
        if api_key:
            params['api_key'] = api_key
            query = "SELECT * FROM session WHERE sid=:sid AND api_key=:api_key"

        with db.engine.connect() as connection:
            result = connection.execute(text(query), params)
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
        with db.engine.connect() as connection:
            connection.execute(text("INSERT INTO session (user_id, sid, api_key) VALUES (:user_id, :sid, :api_key)"),
                               {'user_id': token.user.id, 'sid': session, 'api_key': token.api_key})
        token.consume()
        return Session.load(session)
