# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals
from db.testing import DatabaseTestCase
import logging
from datetime import datetime
from tests.util import generate_data
from webserver.postgres_connection import init_postgres_connection
import db
from db.mockdata import User, Token, Session
import sqlalchemy


class TestAPICompatUserClass(DatabaseTestCase):

    def setUp(self):
        super(TestAPICompatUserClass, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = init_postgres_connection(self.config.TEST_SQLALCHEMY_DATABASE_URI)

        # Create a user
        uid = db.user.create("test")
        self.assertIsNotNone(db.user.get(uid))
        with db.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text('SELECT * FROM "user" WHERE id = :id'),
                                        {"id": uid})
            self.user = User(result.fetchone())

        # Insert some listens
        date = datetime(2015, 9, 3, 0, 0, 0)
        self.log.info("Inserting test data...")
        test_data = generate_data(date, 100)
        self.logstore.insert_postgresql(test_data)
        self.log.info("Test data inserted")

    def tearDown(self):
        super(TestAPICompatUserClass, self).tearDown()

    def test_user_get_id(self):
        uid = User.get_id(self.user.name)
        self.assertEquals(uid, self.user.id)

    def test_user_load_by_name(self):
        user = User.load_by_name(self.user.name)
        assert isinstance(user, User) == True
        self.assertEquals(user.__dict__, self.user.__dict__)

    def test_user_load_by_id(self):
        user = User.load_by_id(self.user.id)
        assert isinstance(user, User) == True
        self.assertEquals(user.__dict__, self.user.__dict__)

    def test_user_load_by_apikey(self):
        user = User.load_by_apikey(self.user.api_key)
        self.assertEquals(user.__dict__, self.user.__dict__)

    def test_user_get_play_count(self):
        count = User.get_play_count(self.user.name)
        self.assertEquals(count, 100)



class TestAPICompatSessionClass(DatabaseTestCase):

    def setUp(self):
        super(TestAPICompatSessionClass, self).setUp()
        self.log = logging.getLogger(__name__)

    def tearDown(self):
        super(TestAPICompatSessionClass, self).tearDown()

    def test_session_create(self):
        user = User.load_by_id(db.user.create("test"))
        token = Token.generate(user.api_key)
        token.approve(user.name)
        session = Session.create(token)
        self.assertIsNotNone(session)
        self.assertEquals(user.__dict__, session.user.__dict__)

    def test_session_load(self):
        user = User.load_by_id(db.user.create("test"))
        token = Token.generate(user.api_key)
        token.approve(user.name)
        session = Session.create(token)
        self.assertIsNotNone(session)
        self.assertEquals(user.__dict__, session.user.__dict__)
        session.user = None

        # Load with session key
        session2 = Session.load(session.sid)
        self.assertEquals(user.__dict__, session2.__dict__['user'].__dict__)
        session2.user = None
        self.assertEquals(session.__dict__, session2.__dict__)

        # Load with session_key + api_key
        session3 = Session.load(session.sid, session.api_key)
        self.assertEquals(user.__dict__, session3.__dict__['user'].__dict__)
        session3.user = None
        self.assertEquals(session.__dict__, session3.__dict__)
