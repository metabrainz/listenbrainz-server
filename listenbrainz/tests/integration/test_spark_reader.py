from unittest import mock

import orjson

from listenbrainz.db import user as db_user
from listenbrainz.spark.background import BackgroundJobProcessor
from listenbrainz.tests.integration import IntegrationTestCase


class SparkReaderTestCase(IntegrationTestCase):

    def test_import_similar_users(self):
        user_id_21 = db_user.create(self.db_conn, 21, "twenty_one")
        user_id_22 = db_user.create(self.db_conn, 22, "twenty_two")
        user_id_23 = db_user.create(self.db_conn, 23, "twenty_three")

        messages = [
            {"type": "similar_users_start"},
            {
                "type": "similar_users",
                "data": [
                    {
                        "user_id": user_id_21,
                        "similar_users": {
                            str(user_id_22): 0.4,
                            str(user_id_23): 0.7,
                        },
                    },
                    {
                        "user_id": user_id_22,
                        "similar_users": {str(user_id_21): 0.4},
                    },
                    {
                        "user_id": user_id_23,
                        "similar_users": {str(user_id_21): 0.7},
                    },
                ],
            },
            {"type": "similar_users_end"},
        ]

        processor = BackgroundJobProcessor(self.app)
        with self.app.app_context():
            for message in messages:
                processor.process_message(
                    mock.Mock(body=orjson.dumps(message))
                )

        self.assertListEqual(
            [
                {
                    "id": user_id_23,
                    "musicbrainz_id": "twenty_three",
                    "similarity": 0.7,
                },
                {
                    "id": user_id_22,
                    "musicbrainz_id": "twenty_two",
                    "similarity": 0.4,
                },
            ],
            db_user.get_similar_users(self.db_conn, user_id_21),
        )
        self.assertListEqual(
            [
                {
                    "id": user_id_21,
                    "musicbrainz_id": "twenty_one",
                    "similarity": 0.4,
                }
            ],
            db_user.get_similar_users(self.db_conn, user_id_22),
        )
        self.assertListEqual(
            [
                {
                    "id": user_id_21,
                    "musicbrainz_id": "twenty_one",
                    "similarity": 0.7,
                }
            ],
            db_user.get_similar_users(self.db_conn, user_id_23),
        )
