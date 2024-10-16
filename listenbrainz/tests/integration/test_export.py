import json
import os
import time
import zipfile
from io import BytesIO

from brainzutils import cache
from sqlalchemy import text

import listenbrainz.db.user as db_user
import listenbrainz.db.pinned_recording as db_pinned_rec
import listenbrainz.db.feedback as db_feedback
from listenbrainz.db.model.feedback import Feedback

from listenbrainz.db.model.pinned_recording import WritablePinnedRecording
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver import db_conn


class ExportTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1799, 'lucifer-export')
        db_user.agree_to_gdpr(self.db_conn, self.user['musicbrainz_id'])
        self.redis = cache._r

    def tearDown(self):
        with self.app.app_context():
            self.redis.flushall()
        for archive in os.listdir(self.app.config["USER_DATA_EXPORT_BASE_DIR"]):
            os.remove(os.path.join(self.app.config["USER_DATA_EXPORT_BASE_DIR"], archive))
        super(ExportTestCase, self).tearDown()

    def send_listens(self):
        with open(self.path_to_data_file('user_export_test.json')) as f:
            payload = json.load(f)
        response = self.client.post(
            self.custom_url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        time.sleep(1)
        recalculate_all_user_data()
        return response

    def test_export(self):
        self.temporary_login(self.user['login_id'])

        self.send_listens()
        url = self.custom_url_for('api_v1.get_listens', user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, 1, query_string={'count': '1'})
        data = json.loads(response.data)['payload']
        self.assert200(response)

        pinned_recordings = [
            {
                "recording_msid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
                "recording_mbid": "83b57de1-7f69-43cb-a0df-5f77a882e954",
                "blurb_content": "Amazing first recording",
            },
            {
                "recording_msid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
                "recording_mbid": "7e4142f4-b01e-4492-ae13-553493bad634",
                "blurb_content": "Wonderful second recording",
            },
        ]
        for pin_rec in pinned_recordings:
            db_pinned_rec.pin(
                self.db_conn,
                WritablePinnedRecording(
                    user_id=self.user["id"],
                    recording_msid=pin_rec["recording_msid"],
                    recording_mbid=pin_rec["recording_mbid"],
                    blurb_content=pin_rec["blurb_content"],
                )
            )

        feedback = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "score": 1
            },
            {
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "score": -1
            },
            {
                "recording_mbid": "076255b4-1575-11ec-ac84-135bf6a670e3",
                "score": 1
            },
            {
                "recording_mbid": "1fd178b4-1575-11ec-b98a-d72392cd8c97",
                "score": -1
            }
        ]
        for fb in feedback:
            db_feedback.insert(
                self.db_conn,
                Feedback(
                    user_id=self.user["id"],
                    recording_msid=fb.get("recording_msid"),
                    recording_mbid=fb.get("recording_mbid"),
                    score=fb["score"]
                )
            )

        response = self.client.post(self.custom_url_for('export.create_export_task'))
        self.assert200(response)
        export_id = response.json["export_id"]

        response = self.client.get(self.custom_url_for('export.get_export_task', export_id=export_id))
        self.assert200(response)
        self.assertEqual(export_id, response.json["export_id"])
        self.assertIn("type", response.json)
        self.assertIn("available_until", response.json)
        self.assertIn("created", response.json)
        self.assertIn("progress", response.json)
        self.assertIn("status", response.json)
        self.assertIn("filename", response.json)

        response = self.client.get(self.custom_url_for('export.list_export_tasks'))
        self.assert200(response)
        self.assertEqual(1, len(response.json))
        self.assertEqual(export_id, response.json[0]["export_id"])
        self.assertIn("type", response.json[0])
        self.assertIn("available_until", response.json[0])
        self.assertIn("created", response.json[0])
        self.assertIn("progress", response.json[0])
        self.assertIn("status", response.json[0])
        self.assertIn("filename", response.json[0])

        for _ in range(60):
            response = self.client.post(self.custom_url_for("export.download_export_archive", export_id=export_id))
            if response.status_code == 404:
                time.sleep(1)  # wait for export to finish
                continue
            else:
                break
        for task in db_conn.execute(text("SELECT * FROM user_data_export")).all():
            print(task)
        self.assert200(response)
        with zipfile.ZipFile(BytesIO(response.data), "r") as export_zip:
            export_zip.printdir()
            with export_zip.open("user.json", "r") as f:
                data = json.load(f)
                self.assertEqual(data, {
                  "user_id": self.user["id"],
                  "username": "lucifer-export"
                })
            with export_zip.open("listens/2021/4.jsonl", "r") as f:
                listens = []
                for line in f:
                    listens.append(json.loads(line.strip()))

            with open(self.path_to_data_file('user_export_test.json')) as f:
                payload = json.load(f)

            payload["payload"].sort(key=lambda l: l["listened_at"])
            listens.sort(key=lambda l: l["listened_at"])

            for expected, received in zip(payload["payload"], listens):
                self.assertEqual(expected["track_metadata"]["track_name"], received["track_metadata"]["track_name"])
                self.assertEqual(expected["track_metadata"]["artist_name"], received["track_metadata"]["artist_name"])
                self.assertEqual(expected["track_metadata"]["release_name"], received["track_metadata"]["release_name"])
                self.assertEqual(expected["listened_at"], received["listened_at"])

            with export_zip.open("pinned_recording.jsonl", "r") as f:
                received_pins = []
                for line in f:
                    received_pins.append(json.loads(line.strip()))

            for expected, received in zip(pinned_recordings, received_pins):
                self.assertEqual(expected["recording_msid"], received["recording_msid"])
                self.assertEqual(expected["recording_mbid"], received["recording_mbid"])
                self.assertEqual(expected["blurb_content"], received["blurb_content"])

            with export_zip.open("feedback.jsonl", "r") as f:
                received_feedback = []
                for line in f:
                    received_feedback.append(json.loads(line.strip()))

            for expected, received in zip(feedback, received_feedback):
                self.assertEqual(expected.get("recording_msid"), received.get("recording_msid"))
                self.assertEqual(expected.get("recording_mbid"), received.get("recording_mbid"))
                self.assertEqual(expected["score"], received["score"])

        response = self.client.post(self.custom_url_for('export.delete_export_archive', export_id=export_id))
        self.assert200(response)

        response = self.client.get(self.custom_url_for('export.get_export_task', export_id=export_id))
        self.assert404(response)

        response = self.client.post(self.custom_url_for("export.download_export_archive", export_id=export_id))
        self.assert404(response)

        self.assertEqual(len(os.listdir(self.app.config["USER_DATA_EXPORT_BASE_DIR"])), 0)

