import json
from datetime import datetime

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale
from listenbrainz.messybrainz import update_msids_from_mapping
from listenbrainz.tests.integration import IntegrationTestCase


class MsidUpdaterTestCase(IntegrationTestCase):

    def setUp(self):
        IntegrationTestCase.setUp(self)
        self.user = db_user.get_or_create(self.db_conn, 1111, "msid-updater-user")

    def create_dummy_data(self):
        mapping = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "recording_mbid": "2f3d422f-8890-41a1-9762-fbe16f107c31"
            },
            {
                "recording_msid": "667e797d-75ee-42d5-bdcd-b669f5d70531",
                "recording_mbid": "e9a37376-5e13-4353-989b-acc2f9fbc5b8"
            },
            {
                "recording_msid": "e698826a-dcb0-4162-9418-f2d959a420e2",
                "recording_mbid": "cf4bfb24-1258-4246-9e9f-39c2f216b116"
            },
            {
                "recording_msid": "e8c5f386-2966-4a84-b481-0de2f69ce5c1",
                "recording_mbid": None
            }
        ]
        pinned_recs = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "recording_mbid": "2f3d422f-8890-41a1-9762-fbe16f107c31",
                "blurb_content": "Amazing first recording",
            },
            {
                "recording_msid": "667e797d-75ee-42d5-bdcd-b669f5d70531",
                "recording_mbid": None,
                "blurb_content": "Wonderful second recording",
            },
            {
                "recording_msid": "e8c5f386-2966-4a84-b481-0de2f69ce5c1",
                "recording_mbid": None,
                "blurb_content": "Incredible third recording",
            },
            {
                "recording_msid": None,
                "recording_mbid": "cf4bfb24-1258-4246-9e9f-39c2f216b116",
                "blurb_content": "Great fourth recording",
            }
        ]
        recording_feedback = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "recording_mbid": None,
                "score": 1
            },
            {
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "recording_mbid": None,
                "score": -1
            },
            {
                "recording_msid": None,
                "recording_mbid": "9541592c-0102-4b94-93cc-ee0f3cf83d64",
                "score": 1
            },
            {
                "recording_msid": "9d008211-c920-4ff7-a17f-b86e4246c58c",
                "recording_mbid": "e7ebbb99-7346-4323-9541-dffae9e1003b",
                "score": -1
            }
        ]
        user_timeline_event = [
            {
                "event_type": "recording_recommendation",
                "metadata": {
                    "track_name": "Sunflower",
                    "artist_name": "Swae Lee & Post Malone",
                    "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f"
                }
            },
            {
                "event_type": "personal_recording_recommendation",
                "metadata": {
                    "track_name": "Sunflower",
                    "artist_name": "Swae Lee & Post Malone",
                    "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                    "users": [1, 4],
                    "blurb_content": "Amazing recording!"
                }
            },
            {
                "event_type": "recording_recommendation",
                "metadata": {
                    "track_name": "Batman",
                    "artist_name": "Danny Elfman",
                    "recording_msid": "667e797d-75ee-42d5-bdcd-b669f5d70531",
                    "recording_mbid": None
                }
            },
            {
                "event_type": "recording_recommendation",
                "metadata": {
                    "track_name": "Portishead",
                    "artist_name": "Strangers",
                    "recording_msid": "e8c5f386-2966-4a84-b481-0de2f69ce5c1"
                }
            },
            {
                "event_type": "personal_recording_recommendation",
                "metadata": {
                    "track_name": "Strangers",
                    "artist_name": "Portishead",
                    "recording_msid": "e8c5f386-2966-4a84-b481-0de2f69ce5c1",
                    "recording_mbid": None
                }
            },
            {
                "event_type": "recording_recommendation",
                "metadata": {
                    "track_name": "Wolfs",
                    "artist_name": "Selena Gomez",
                    "recording_msid": "e698826a-dcb0-4162-9418-f2d959a420e2",
                    "recording_mbid": "cf4bfb24-1258-4246-9e9f-39c2f216b116"
                }
            }
        ]
        mapping_query = """
            INSERT INTO mbid_mapping (recording_msid, recording_mbid, match_type)
                 VALUES (:recording_msid, :recording_mbid, :match_type)
        """
        with timescale.engine.begin() as conn:
            for item in mapping:
                conn.execute(text(mapping_query), {
                    "recording_msid": item["recording_msid"],
                    "recording_mbid": item["recording_mbid"],
                    "match_type": "exact_match" if item["recording_mbid"] else "no_match"
                })

        pin_rec_query = """
            INSERT INTO pinned_recording (user_id, recording_msid, recording_mbid, blurb_content, pinned_until)
                 VALUES (:user_id, :recording_msid, :recording_mbid, :blurb_content, :pinned_until)
        """
        feedback_query = """
            INSERT INTO recording_feedback (user_id, recording_msid, recording_mbid, score)
                 VALUES (:user_id, :recording_msid, :recording_mbid, :score)
        """
        timeline_query = """
            INSERT INTO user_timeline_event (user_id, event_type, metadata)
                 VALUES (:user_id, :event_type, :metadata)
        """
        for item in pinned_recs:
            self.db_conn.execute(text(pin_rec_query), {"user_id": self.user["id"], "pinned_until": datetime.now(), **item})

        for item in recording_feedback:
            self.db_conn.execute(text(feedback_query), {"user_id": self.user["id"], **item})

        for item in user_timeline_event:
            self.db_conn.execute(text(timeline_query), {
                "user_id": self.user["id"],
                "event_type": item["event_type"],
                "metadata": json.dumps(item["metadata"])
            })
        self.db_conn.commit()

    def test_msid_updater(self):
        self.create_dummy_data()
        with self.app.app_context():
            update_msids_from_mapping.run_all_updates()

        expected_feedback = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "recording_mbid": "2f3d422f-8890-41a1-9762-fbe16f107c31",
                "score": 1
            },
            {
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "recording_mbid": None,
                "score": -1
            },
            {
                "recording_msid": None,
                "recording_mbid": "9541592c-0102-4b94-93cc-ee0f3cf83d64",
                "score": 1
            },
            {
                "recording_msid": "9d008211-c920-4ff7-a17f-b86e4246c58c",
                "recording_mbid": "e7ebbb99-7346-4323-9541-dffae9e1003b",
                "score": -1
            }
        ]
        expected_pinned_recs = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "recording_mbid": "2f3d422f-8890-41a1-9762-fbe16f107c31",
                "blurb_content": "Amazing first recording",
            },
            {
                "recording_msid": "667e797d-75ee-42d5-bdcd-b669f5d70531",
                "recording_mbid": "e9a37376-5e13-4353-989b-acc2f9fbc5b8",
                "blurb_content": "Wonderful second recording",
            },
            {
                "recording_msid": "e8c5f386-2966-4a84-b481-0de2f69ce5c1",
                "recording_mbid": None,
                "blurb_content": "Incredible third recording",
            },
            {
                "recording_msid": None,
                "recording_mbid": "cf4bfb24-1258-4246-9e9f-39c2f216b116",
                "blurb_content": "Great fourth recording",
            }
        ]
        expected_timeline_event = [
            {
                "event_type": "recording_recommendation",
                "metadata": {
                    "track_name": "Sunflower",
                    "artist_name": "Swae Lee & Post Malone",
                    "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                    "recording_mbid": "2f3d422f-8890-41a1-9762-fbe16f107c31"
                }
            },
            {
                "event_type": "personal_recording_recommendation",
                "metadata": {
                    "track_name": "Sunflower",
                    "artist_name": "Swae Lee & Post Malone",
                    "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                    "users": [1, 4],
                    "blurb_content": "Amazing recording!",
                    "recording_mbid": "2f3d422f-8890-41a1-9762-fbe16f107c31"
                }
            },
            {
                "event_type": "recording_recommendation",
                "metadata": {
                    "track_name": "Batman",
                    "artist_name": "Danny Elfman",
                    "recording_msid": "667e797d-75ee-42d5-bdcd-b669f5d70531",
                    "recording_mbid": "e9a37376-5e13-4353-989b-acc2f9fbc5b8"
                }
            },
            {
                "event_type": "recording_recommendation",
                "metadata": {
                    "track_name": "Portishead",
                    "artist_name": "Strangers",
                    "recording_msid": "e8c5f386-2966-4a84-b481-0de2f69ce5c1"
                }
            },
            {
                "event_type": "personal_recording_recommendation",
                "metadata": {
                    "track_name": "Strangers",
                    "artist_name": "Portishead",
                    "recording_msid": "e8c5f386-2966-4a84-b481-0de2f69ce5c1",
                    "recording_mbid": None
                }
            },
            {
                "event_type": "recording_recommendation",
                "metadata": {
                    "track_name": "Wolfs",
                    "artist_name": "Selena Gomez",
                    "recording_msid": "e698826a-dcb0-4162-9418-f2d959a420e2",
                    "recording_mbid": "cf4bfb24-1258-4246-9e9f-39c2f216b116"
                }
            }
        ]

        result = self.db_conn.execute(text("SELECT recording_msid::text, recording_mbid::text, score FROM recording_feedback"))
        self.assertCountEqual(result.mappings().all(), expected_feedback)

        result = self.db_conn.execute(text("SELECT recording_msid::text, recording_mbid::text, blurb_content FROM pinned_recording"))
        self.assertCountEqual(result.mappings().all(), expected_pinned_recs)

        result = self.db_conn.execute(text("SELECT event_type, metadata FROM user_timeline_event"))
        self.assertCountEqual(result.mappings().all(), expected_timeline_event)
