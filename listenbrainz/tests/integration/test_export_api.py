import json
import os
import time
import zipfile
from io import BytesIO

from brainzutils import cache
from sqlalchemy import text

import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.pinned_recording as db_pinned_rec
import listenbrainz.db.user as db_user
from listenbrainz.background.export import export_user, cleanup_old_exports
from listenbrainz.db.model.feedback import Feedback
from listenbrainz.db.model.pinned_recording import WritablePinnedRecording
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver import db_conn


class ExportAPITestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1799, 'adeeb-export-api')
        db_user.agree_to_gdpr(self.db_conn, self.user['musicbrainz_id'])
        self.redis = cache._r
        self.recording = {
            "recording_mbid": "6b64a82d-0aa8-430e-bf25-26aa4c569af0",
            "artist_mbids": ["d15721d8-56b4-453d-b506-fc915b14cba2"],
            "release_mbid": "f10badef-094b-48b1-b345-cddfc3d41673",
            "recording_data": {
                "name": "Sister",
                "rels": [
                    {
                        "type": "performer", "artist_mbid": "d15721d8-56b4-453d-b506-fc915b14cba2",
                        "artist_name": "The Black Keys"
                    }
                ],
                "length": 205000
            },
            "artist_data": {
                "name": "The Black Keys",
                "artists": [
                    {
                        "area": "United States",
                        "name": "The Black Keys",
                        "rels": {
                            "lyrics": "https://www.musixmatch.com/artist/The-Black-Keys",
                            "youtube": "https://www.youtube.com/channel/UCJL3h2-wEOB6EigQOBZ3ryg",
                            "wikidata": "https://www.wikidata.org/wiki/Q606226",
                            "streaming": "https://tidal.com/artist/64643",
                            "free streaming": "https://www.deezer.com/artist/2483",
                            "social network": "https://www.instagram.com/theblackkeys/",
                            "official homepage": "https://www.theblackkeys.com/",
                            "purchase for download": "https://www.qobuz.com/us-en/interpreter/-/40589",
                            "purchase for mail-order": "https://www.cdjapan.co.jp/person/700225155"},
                        "type": "Group", "begin_year": 2001,
                        "join_phrase": ""}
                ],
                "artist_credit_id": 59036
            },
            "tag_data": {},
            "release_data": {
                "mbid": "f10badef-094b-48b1-b345-cddfc3d41673",
                "name": "El Camino",
                "year": 2011,
                "caa_id": 39543436175,
                "caa_release_mbid": "2fa2b8f0-e4ab-46e8-8ab4-91d0e1aecfad",
                "album_artist_name": "The Black Keys",
                "release_group_mbid": "c2eed4c1-5cd9-469a-9075-b82077093967"
            },
        }

    def tearDown(self):
        with self.app.app_context():
            self.redis.flushall()
        for archive in os.listdir(self.app.config["USER_DATA_EXPORT_BASE_DIR"]):
            os.remove(os.path.join(self.app.config["USER_DATA_EXPORT_BASE_DIR"], archive))
        super(ExportAPITestCase, self).tearDown()

    def create_mapping_record(self, recording_msid):
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_metadata_cache
                    (recording_mbid, artist_mbids, release_mbid, recording_data, artist_data, tag_data, release_data, dirty)
             VALUES (:recording_mbid ::UUID, :artist_mbids ::UUID[], :release_mbid ::UUID, :recording_data, :artist_data, :tag_data, :release_data, 'f')
        """), {
            "recording_mbid": self.recording["recording_mbid"],
            "artist_mbids": self.recording["artist_mbids"],
            "release_mbid": self.recording["release_mbid"],
            "recording_data": json.dumps(self.recording["recording_data"]),
            "artist_data": json.dumps(self.recording["artist_data"]),
            "release_data": json.dumps(self.recording["release_data"]),
            "tag_data": json.dumps(self.recording["tag_data"])
        })
        self.ts_conn.execute(text("""
            INSERT INTO mbid_mapping (recording_msid, recording_mbid, match_type)
             VALUES (:recording_msid, :recording_mbid, 'exact_match')
        """), {
            "recording_msid": recording_msid,
            "recording_mbid": self.recording["recording_mbid"]
        })
        self.ts_conn.commit()

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

    def test_export_api(self):
        # We don't login via session for API tests, we use the Token in headers
        auth_header = {'Authorization': 'Token {}'.format(self.user['auth_token'])}

        self.send_listens()
        url = self.custom_url_for('api_v1.get_listens', user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, 1, query_string={'count': '3'})
        data = json.loads(response.data)['payload']
        self.assert200(response)
        recording_msid = data["listens"][1]["recording_msid"]
        self.create_mapping_record(recording_msid)

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

        # Create export
        response = self.client.post(self.custom_url_for('export_api.create_export_task'), headers=auth_header)
        self.assert200(response)
        export_id = response.json["export_id"]

        # Get status
        response = self.client.get(self.custom_url_for('export_api.get_export_task', export_id=export_id), headers=auth_header)
        self.assert200(response)
        self.assertEqual(export_id, response.json["export_id"])
        self.assertEqual("waiting", response.json["status"])

        # List exports
        response = self.client.get(self.custom_url_for('export_api.list_export_tasks'), headers=auth_header)
        self.assert200(response)
        self.assertEqual(1, len(response.json))
        self.assertEqual(export_id, response.json[0]["export_id"])

        # Wait for export to finish
        for _ in range(60):
            response = self.client.get(self.custom_url_for("export_api.download_export_archive", export_id=export_id), headers=auth_header)
            if response.status_code == 404:
                time.sleep(1)  # wait for export to finish
                continue
            else:
                break

        self.assert200(response)

        # Verify zip content
        with zipfile.ZipFile(BytesIO(response.data), "r") as export_zip:
            with export_zip.open("user.json", "r") as f:
                data = json.load(f)
                self.assertEqual(data, {
                  "user_id": self.user["id"],
                  "username": "adeeb-export-api"
                })

        # Delete export
        response = self.client.post(self.custom_url_for('export_api.delete_export_archive', export_id=export_id), headers=auth_header)
        self.assert200(response)

        # Verify deletion
        response = self.client.get(self.custom_url_for('export_api.get_export_task', export_id=export_id), headers=auth_header)
        self.assert404(response)
