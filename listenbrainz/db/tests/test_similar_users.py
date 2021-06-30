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
        user_id = db_user.create(1, "tom")
        user_id2 = db_user.create(2, "jerry")

        with db.engine.connect() as connection:
            connection.execute(sqlalchemy.text("""INSERT INTO recommendation.similar_user (user_id, similar_users)
                                                       VALUES (1, '{ "jerry" : [0.42, 0.01] }')"""))
            connection.execute(sqlalchemy.text("""INSERT INTO recommendation.similar_user (user_id, similar_users)
                                                       VALUES (2, '{ "tom" : [0.42, 0.02] }')"""))

        similar_users = get_top_similar_users()
        assert len(similar_users) == 1
        assert similar_users[0][0] == 'jerry'
        assert similar_users[0][1] == 'tom'
        assert similar_users[0][2] == "0.420"

        similar_users = get_top_similar_users(global_similarity=True)
        assert len(similar_users) == 1
        assert similar_users[0][0] == 'jerry'
        assert similar_users[0][1] == 'tom'
        assert similar_users[0][2] == "0.020"
