# -*- coding: utf-8 -*-

import listenbrainz.db.user as db_user
import listenbrainz.db.spotify as db_spotify
import listenbrainz.db.stats as db_stats
import sqlalchemy
import time
import ujson

from listenbrainz import db
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.similar_users import get_top_similar_users


class SimilarUserTestCase(DatabaseTestCase):
    def test_fetch_top_similar_users(self):
        user_id = db_user.create(0, "izzy_cheezy")
        with db.engine.connect() as connection:
            with connection.connection.cursor() as curs:
                curs.execute("""INSERT INTO recommendation.similar_user (user_id, similar_users)
                                     VALUES (1, '{ "scooby" : ".42" }')""")


        similar_users = get_top_similar_users()
        assert len(similar_users) == 1
        assert similar_users[0][0] == 'izzy_cheezy'
        assert similar_users[0][1] == 'scooby'
        assert similar_users[0][2] == '.42'
