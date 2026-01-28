import listenbrainz.db.user as db_user
from listenbrainz.db.lastfm_session import Session
from listenbrainz.db.lastfm_token import Token
from listenbrainz.db.lastfm_user import User
from listenbrainz.db.testing import DatabaseTestCase


class TestAPICompatSessionClass(DatabaseTestCase):

    def test_session_create(self):
        user = User.load_by_id(self.db_conn, db_user.create(self.db_conn, 1, "test"))
        token = Token.generate(self.db_conn, user.api_key)
        token.approve(self.db_conn, user.name)
        session = Session.create(self.db_conn, token)
        self.assertIsInstance(session, Session)
        self.assertDictEqual(user.__dict__, session.user.__dict__)

    def test_session_load(self):
        user = User.load_by_id(self.db_conn, db_user.create(self.db_conn, 1, "test"))
        token = Token.generate(self.db_conn, user.api_key)
        token.approve(self.db_conn, user.name)
        session = Session.create(self.db_conn, token)
        self.assertIsInstance(session, Session)
        self.assertDictEqual(user.__dict__, session.user.__dict__)
        session.user = None

        # Load with session_key + api_key
        session2 = Session.load(self.db_conn, session.sid)
        self.assertDictEqual(user.__dict__, session2.__dict__['user'].__dict__)
        session2.user = None
        self.assertDictEqual(session.__dict__, session2.__dict__)
