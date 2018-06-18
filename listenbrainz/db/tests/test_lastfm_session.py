
import logging

import listenbrainz.db.user as db_user
from listenbrainz.db.lastfm_session import Session
from listenbrainz.db.lastfm_token import Token
from listenbrainz.db.lastfm_user import User
from listenbrainz.db.testing import DatabaseTestCase


class TestAPICompatSessionClass(DatabaseTestCase):

    def setUp(self):
        super(TestAPICompatSessionClass, self).setUp()
        self.log = logging.getLogger(__name__)

    def tearDown(self):
        super(TestAPICompatSessionClass, self).tearDown()

    def test_session_create(self):
        user = User.load_by_id(db_user.create(1, "test"))
        token = Token.generate(user.api_key)
        token.approve(user.name)
        session = Session.create(token)
        self.assertIsInstance(session, Session)
        self.assertDictEqual(user.__dict__, session.user.__dict__)

    def test_session_load(self):
        user = User.load_by_id(db_user.create(1, "test"))
        token = Token.generate(user.api_key)
        token.approve(user.name)
        session = Session.create(token)
        self.assertIsInstance(session, Session)
        self.assertDictEqual(user.__dict__, session.user.__dict__)
        session.user = None

        # Load with session_key + api_key
        session2 = Session.load(session.sid)
        self.assertDictEqual(user.__dict__, session2.__dict__['user'].__dict__)
        session2.user = None
        self.assertDictEqual(session.__dict__, session2.__dict__)
