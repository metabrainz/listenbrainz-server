
import logging
import uuid
from datetime import timedelta

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz import db
from listenbrainz.db.lastfm_token import Token, TOKEN_EXPIRATION_TIME
from listenbrainz.db.lastfm_user import User
from listenbrainz.db.testing import DatabaseTestCase


class TestAPICompatTokenClass(DatabaseTestCase):

    def setUp(self):
        super(TestAPICompatTokenClass, self).setUp()
        self.log = logging.getLogger(__name__)

        # Create a user
        uid = db_user.create(1, "test")
        self.assertIsNotNone(db_user.get(uid))
        with db.engine.connect() as connection:
            result = connection.execute(text('SELECT * FROM "user" WHERE id = :id'),
                                        {"id": uid})
            row = result.fetchone()
            self.user = User(row.id, row.created, row.musicbrainz_id, row.auth_token)

    def tearDown(self):
        super(TestAPICompatTokenClass, self).tearDown()

    def test_is_valid_api_key(self):
        self.assertTrue(Token.is_valid_api_key(self.user.api_key))
        self.assertTrue(Token.is_valid_api_key(str(uuid.uuid4())))

    def test_load(self):
        token = Token.generate(self.user.api_key)
        self.assertIsInstance(token, Token)
        self.assertIsNone(token.user)

        """ Before approving """
        # Load with token
        token1 = Token.load(token.token)
        self.assertIsNone(token1.user)
        self.assertDictEqual(token1.__dict__, token.__dict__)

        # Load with token & api_key
        token2 = Token.load(token.token, token.api_key)
        self.assertIsNone(token2.user)
        self.assertDictEqual(token2.__dict__, token.__dict__)

        token.approve(self.user.name)

        """ After approving the token """
        # Load with token
        token1 = Token.load(token.token)
        self.assertIsInstance(token1.user, User)
        self.assertDictEqual(token1.user.__dict__, token.user.__dict__)
        token_user = token.user
        token.user, token1.user = None, None
        self.assertDictEqual(token1.__dict__, token.__dict__)
        token.user = token_user

        # Load with token & api_key
        token2 = Token.load(token.token, token.api_key)
        self.assertIsInstance(token2.user, User)
        self.assertDictEqual(token2.user.__dict__, token.user.__dict__)
        token.user, token1.user = None, None
        self.assertDictEqual(token1.__dict__, token.__dict__)

    def test_generate(self):
        token = Token.generate(str(uuid.uuid4()))
        self.assertIsInstance(token, Token)

    def test_has_expired(self):
        token = Token.generate(str(uuid.uuid4()))
        self.assertFalse(token.has_expired())
        token.timestamp = token.timestamp - timedelta(minutes=TOKEN_EXPIRATION_TIME - 1)
        # This is asssertFalse because in the next 1 minute the next statement will get executed
        self.assertFalse(token.has_expired())
        token.timestamp = token.timestamp - timedelta(minutes=1)
        self.assertTrue(token.has_expired())

    def test_approve(self):
        token = Token.generate(str(uuid.uuid4()))
        self.assertIsInstance(token, Token)
        self.assertIsNone(token.user)
        before_token = token.__dict__
        before_token.pop('user')

        token.approve(self.user.name)

        after_token = token.__dict__
        self.assertIsInstance(token.user, User)
        self.assertDictEqual(token.user.__dict__, self.user.__dict__)
        after_token.pop('user')

        self.assertDictEqual(after_token, before_token)
