import json
import time
import zipfile
from io import BytesIO

from brainzutils import cache

import listenbrainz.db.user as db_user
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase


class ExportTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1799, 'lucifer-export')
        db_user.agree_to_gdpr(self.db_conn, self.user['musicbrainz_id'])
        self.redis = cache._r

    def tearDown(self):
        with self.app.app_context():
            self.redis.flushall()
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
        url = self.custom_url_for('api_v1.get_listens',
                                  user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, 1, query_string={'count': '1'})
        data = json.loads(response.data)['payload']
        self.assert200(response)

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

        for _ in range(30):
            response = self.client.post(self.custom_url_for("export.download_export_archive", export_id=export_id))
            if response.status_code == 404:
                time.sleep(1)  # wait for export to finish
                continue
            else:
                break

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
