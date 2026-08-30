import json
import os
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from unittest import mock

from brainzutils import cache
from minio.deleteobjects import DeleteObject
from sqlalchemy import text

import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.pinned_recording as db_pinned_rec
import listenbrainz.db.user as db_user
from listenbrainz.background.export import EXPORT_FAILED_PROGRESS, cleanup_old_exports, export_user
from listenbrainz.background.migrate_exports import ARCHIVE_MISSING_PROGRESS, migrate_exports
from listenbrainz.db.model.feedback import Feedback
from listenbrainz.db.model.pinned_recording import WritablePinnedRecording
from listenbrainz.garage import ensure_bucket, get_garage_client, get_user_data_export_bucket
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver import db_conn, ts_conn


class ExportTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1799, 'lucifer-export')
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
            client, bucket = self.get_export_storage()
            objects = [DeleteObject(obj.object_name) for obj in client.list_objects(bucket)]
            for error in client.remove_objects(bucket, objects):
                self.fail(f"Failed to remove export {error.name}: {error.message}")
        super(ExportTestCase, self).tearDown()

    def get_export_storage(self):
        """ Get the garage client and the bucket user data exports are stored in. """
        client = get_garage_client()
        bucket = get_user_data_export_bucket()
        ensure_bucket(client, bucket)
        return client, bucket

    def create_mapping_record(self, recording_msid):
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_metadata_cache
                    (recording_mbid, recording_id, artist_mbids, artist_ids, release_mbid, release_id, recording_data, artist_data, tag_data, release_data, dirty)
             VALUES (:recording_mbid ::UUID, 1, :artist_mbids ::UUID[], '{1}'::INTEGER[], :release_mbid ::UUID, 1, :recording_data, :artist_data, :tag_data, :release_data, 'f')
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

    def test_export(self):
        self.temporary_login(self.user['login_id'])

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

        self.assert200(response)
        with zipfile.ZipFile(BytesIO(response.data), "r") as export_zip:
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
                # The test data used in send_listens cannot have an inserted_at prop as that is not a valid listen format
                self.assertNotIn("inserted_at", expected)
                # However inserted_at should be part of the exported listen data
                self.assertIn("inserted_at", received)
                if received["track_metadata"]["track_name"] == "Sister":
                    self.assertEqual({
                        "caa_id": self.recording["release_data"]["caa_id"],
                        "caa_release_mbid": self.recording["release_data"]["caa_release_mbid"],
                        "artist_mbids": self.recording["artist_mbids"],
                        "recording_name": self.recording["recording_data"]["name"],
                        "recording_mbid": self.recording["recording_mbid"],
                        "release_mbid": self.recording["release_data"]["mbid"],
                        "artists": [
                            {
                                "artist_mbid": "d15721d8-56b4-453d-b506-fc915b14cba2",
                                "join_phrase": "",
                                "artist_credit_name": "The Black Keys"
                            }
                        ],
                    }, received["track_metadata"]["mbid_mapping"])
                else:
                    self.assertEqual(None, received["track_metadata"]["mbid_mapping"])

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

        with self.app.app_context():
            cleanup_old_exports(db_conn)
            client, bucket = self.get_export_storage()
            self.assertEqual([obj.object_name for obj in client.list_objects(bucket)], [])

    def create_export_row(self, filename, status="completed", available_until=None, user=None):
        """ Insert a user data export row directly, as if it had been created by an earlier export. """
        if available_until is None:
            available_until = datetime.now() + timedelta(days=30)
        result = self.db_conn.execute(text("""
            INSERT INTO user_data_export (user_id, type, status, progress, filename, available_until)
                 VALUES (:user_id, 'export_all_user_data', :status, 'Export completed', :filename, :available_until)
              RETURNING id
        """), {
            "user_id": (user or self.user)["id"],
            "status": status,
            "filename": filename,
            "available_until": available_until,
        })
        self.db_conn.commit()
        return result.first().id

    def get_export_row(self, export_id):
        result = self.db_conn.execute(
            text("SELECT status, progress FROM user_data_export WHERE id = :export_id"),
            {"export_id": export_id}
        )
        return result.first()

    def test_migrate_exports(self):
        migrated_name = "listenbrainz_lucifer-export_1.zip"
        orphan_name = "listenbrainz_lucifer-export_2.zip"
        missing_name = "listenbrainz_lucifer-export_3.zip"

        migrated_id = self.create_export_row(migrated_name)
        missing_id = self.create_export_row(missing_name)

        with tempfile.TemporaryDirectory() as export_dir:
            for name in (migrated_name, orphan_name):
                with open(os.path.join(export_dir, name), "wb") as f:
                    f.write(b"archive contents of " + name.encode())

            with self.app.app_context():
                client, bucket = self.get_export_storage()

                migrate_exports(db_conn, export_dir, dry_run=True)
                self.assertEqual([obj.object_name for obj in client.list_objects(bucket)], [])
                self.assertEqual("completed", self.get_export_row(missing_id).status)

                migrate_exports(db_conn, export_dir)

                # the archive with an export row is uploaded, the orphan one is not
                self.assertEqual([migrated_name], [obj.object_name for obj in client.list_objects(bucket)])
                archive = client.get_object(bucket, migrated_name)
                self.assertEqual(b"archive contents of " + migrated_name.encode(), archive.read())
                archive.close()
                archive.release_conn()

                # source files are kept unless asked otherwise
                self.assertEqual({migrated_name, orphan_name}, set(os.listdir(export_dir)))

                # the export whose archive is nowhere to be found cannot be migrated
                missing_export = self.get_export_row(missing_id)
                self.assertEqual("failed", missing_export.status)
                self.assertEqual(ARCHIVE_MISSING_PROGRESS, missing_export.progress)
                self.assertEqual("completed", self.get_export_row(migrated_id).status)

                # re-running does not upload again and removes the source files when asked to
                migrate_exports(db_conn, export_dir, delete_source=True)
                self.assertEqual([migrated_name], [obj.object_name for obj in client.list_objects(bucket)])
                self.assertEqual([], os.listdir(export_dir))

    def put_archive(self, filename, contents=b"archive contents"):
        """ Put an archive in the export bucket, as if an earlier export had uploaded it. """
        with self.app.app_context():
            client, bucket = self.get_export_storage()
            client.put_object(bucket, filename, BytesIO(contents), len(contents))

    def list_archives(self):
        with self.app.app_context():
            client, bucket = self.get_export_storage()
            return [obj.object_name for obj in client.list_objects(bucket)]

    def test_export_endpoints_only_serve_the_owner(self):
        """ An export must not be readable or deletable by any user other than its owner. """
        filename = "listenbrainz_lucifer-export_7.zip"
        export_id = self.create_export_row(filename)
        self.put_archive(filename)

        other_user = db_user.get_or_create(self.db_conn, 1800, "lucifer-export-other")
        db_user.agree_to_gdpr(self.db_conn, other_user["musicbrainz_id"])
        self.temporary_login(other_user["login_id"])

        response = self.client.get(self.custom_url_for("export.get_export_task", export_id=export_id))
        self.assert404(response)

        response = self.client.get(self.custom_url_for("export.list_export_tasks"))
        self.assert200(response)
        self.assertEqual([], response.json)

        response = self.client.post(self.custom_url_for("export.download_export_archive", export_id=export_id))
        self.assert404(response)

        response = self.client.post(self.custom_url_for("export.delete_export_archive", export_id=export_id))
        self.assert404(response)

        # the owner's export and its archive are untouched
        self.assertEqual("completed", self.get_export_row(export_id).status)
        self.assertEqual([filename], self.list_archives())

    def test_create_export_task_rejects_a_second_request(self):
        """ The unique index only allows one waiting or in progress export per user. """
        self.create_export_row(None, status="waiting")
        self.temporary_login(self.user["login_id"])

        response = self.client.post(self.custom_url_for("export.create_export_task"))
        self.assert400(response)
        self.assertEqual("Data export already requested.", response.json["error"])

    def test_download_export_archive_when_the_archive_is_missing(self):
        """ The export row may outlive its archive, the migration marks such exports failed. """
        export_id = self.create_export_row("listenbrainz_lucifer-export_8.zip")
        with self.app.app_context():
            self.get_export_storage()  # the bucket exists, only the archive is missing

        self.temporary_login(self.user["login_id"])
        response = self.client.post(self.custom_url_for("export.download_export_archive", export_id=export_id))
        self.assert404(response)

    def test_cleanup_old_exports_removes_expired_exports(self):
        expired_name = "listenbrainz_lucifer-export_9.zip"
        live_name = "listenbrainz_lucifer-export_10.zip"
        expired_id = self.create_export_row(expired_name, available_until=datetime.now() - timedelta(days=1))
        live_id = self.create_export_row(live_name)
        self.put_archive(expired_name)
        self.put_archive(live_name)

        with self.app.app_context():
            cleanup_old_exports(db_conn)

        self.assertIsNone(self.get_export_row(expired_id))
        self.assertIsNotNone(self.get_export_row(live_id))
        self.assertEqual([live_name], self.list_archives())

    def test_export_is_marked_failed_when_the_archive_cannot_be_uploaded(self):
        """ An export left in progress would block the user from ever requesting another one. """
        export_id = self.create_export_row(None, status="waiting")

        with self.app.app_context():
            with mock.patch("listenbrainz.background.export.get_garage_client",
                            side_effect=RuntimeError("garage is unavailable")):
                with self.assertRaises(RuntimeError):
                    export_user(db_conn, ts_conn, self.user["id"], {"export_id": export_id})

        export = self.get_export_row(export_id)
        self.assertEqual("failed", export.status)
        self.assertEqual(EXPORT_FAILED_PROGRESS, export.progress)
        self.assertEqual([], self.list_archives())

        # the user can request a new export, the failed one no longer conflicts with it
        self.create_export_row(None, status="waiting")

    def test_download_export_archive_with_non_ascii_filename(self):
        """ Archive names contain the musicbrainz id which may not be ascii encodable. """
        filename = "listenbrainz_lüdwig_1.zip"
        export_id = self.create_export_row(filename)
        self.put_archive(filename)

        self.temporary_login(self.user["login_id"])
        response = self.client.post(self.custom_url_for("export.download_export_archive", export_id=export_id))
        self.assert200(response)
        self.assertEqual(b"archive contents", response.data)
        self.assertEqual(
            "attachment; filename=listenbrainz_ludwig_1.zip;"
            " filename*=UTF-8''listenbrainz_l%C3%BCdwig_1.zip",
            response.headers["Content-Disposition"]
        )

    def test_migrate_exports_keeps_archives_of_exports_in_progress(self):
        """ An archive of an export that is not completed yet is neither migrated nor deleted. """
        in_progress_name = "listenbrainz_lucifer-export_4.zip"
        migrated_name = "listenbrainz_lucifer-export_5.zip"
        self.create_export_row(in_progress_name, status="in_progress")
        self.create_export_row(migrated_name)

        with tempfile.TemporaryDirectory() as export_dir:
            for name in (in_progress_name, migrated_name):
                with open(os.path.join(export_dir, name), "wb") as f:
                    f.write(b"archive contents of " + name.encode())

            with self.app.app_context():
                client, bucket = self.get_export_storage()
                migrate_exports(db_conn, export_dir, delete_source=True)

                self.assertEqual([migrated_name], [obj.object_name for obj in client.list_objects(bucket)])
                self.assertEqual([in_progress_name], os.listdir(export_dir))

    def test_migrate_exports_does_not_fail_exports_when_no_archive_was_found(self):
        """ Pointing the migration at the wrong directory must not fail every completed export. """
        missing_name = "listenbrainz_lucifer-export_6.zip"
        missing_id = self.create_export_row(missing_name)

        with tempfile.TemporaryDirectory() as export_dir:
            with self.app.app_context():
                self.get_export_storage()

                migrate_exports(db_conn, export_dir)
                self.assertEqual("completed", self.get_export_row(missing_id).status)

                # unless the operator confirms that this is expected
                migrate_exports(db_conn, export_dir, mark_missing_failed=True)
                missing_export = self.get_export_row(missing_id)
                self.assertEqual("failed", missing_export.status)
                self.assertEqual(ARCHIVE_MISSING_PROGRESS, missing_export.progress)
