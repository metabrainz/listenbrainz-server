import json

import listenbrainz.db.user as db_user
import sqlalchemy

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.similar_users import get_top_similar_users


class SimilarUserTestCase(DatabaseTestCase):

    def test_fetch_top_similar_users(self):
        user_id_1 = db_user.create(self.db_conn, 1, "tom")
        user_id_2 = db_user.create(self.db_conn, 2, "jerry")

        similar_users_1 = {user_id_2: 0.42}
        similar_users_2 = {user_id_1: 0.02}

        self.db_conn.execute(sqlalchemy.text("""
        INSERT INTO recommendation.similar_user (user_id, similar_users)
             VALUES (:user_id_1, :similar_users_1), (:user_id_2, :similar_users_2)
        """), {
            "user_id_1": user_id_1,
            "similar_users_1": json.dumps(similar_users_1),
            "user_id_2": user_id_2,
            "similar_users_2": json.dumps(similar_users_2)
        })

        similar_users = get_top_similar_users(self.db_conn)
        assert len(similar_users) == 1
        assert similar_users[0][0] == "jerry"
        assert similar_users[0][1] == "tom"
        assert similar_users[0][2] == "0.020"
