"""
This module contains classes required by the compact API.
"""

import os
import binascii
from db import db


class User(object):
    def __init__(self, row):
        serial, created, name, auth_token = row
        self.id = serial
        self.name = name
        self.api_key = auth_token

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
        result = db.session.execute(""" SELECT * FROM "user" WHERE id=:uid """, {"uid": serial})
        db.session.commit()
        row = result.fetchone()
        if row:
            return User(row)
        return None


class Session(object):
    def __init__(self, row):
        serial, sid, uid, timestamp = row
        self.id = serial
        self.sid = sid
        self.user = User.load_by_id(uid)
        self.timestamp = timestamp

    @staticmethod
    def load(session):
        result = db.session.execute("SELECT * FROM sessions WHERE sid=:sid", {'sid': session})
        db.session.commit()
        row = result.fetchone()
        if row:
            return Session(row)
        return None

    @staticmethod
    def create(user):
        session = binascii.b2a_hex(os.urandom(20))
        db.session.execute("INSERT INTO sessions (sid, uid) VALUES (:sid, :uid)",
                           {'sid': session, 'uid': user.id})
        db.session.commit()
        return Session.load(session)


class Token(object):
    def __init__(self, row):
        id, userid, token, timestamp = row
        self.token = token
        self.timestamp = timestamp
        self.user = None
        if userid:
            self.user = User.load_by_name(userid)

    @staticmethod
    def load(token):
        result = db.session.execute("SELECT * FROM tokens WHERE token=:token",
                           {'token': token})
        db.session.commit()
        row = result.fetchone()
        if row:
            return Token(row)
        return None

    @staticmethod
    def generate():
        token = binascii.b2a_hex(os.urandom(20))
        db.session.execute('INSERT INTO tokens (token) VALUES (:token)',
                           {'token': token})
        db.session.commit()
        return Token.load(token)

    def validate(self, user):
        db.session.execute("UPDATE tokens SET user_id = :uid WHERE token=:token",
                           {'uid': user, 'token': self.token})
        db.session.commit()

    def consume(self):
        db.session.execute("DELETE FROM tokens WHERE token=:token", {'token': self.token})
        db.session.commit()
        self.token = None
        self.timestamp = None
