import io
import json
import os.path
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone, timedelta
from unittest import mock

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.background.listens_importer.storage import cleanup_import_files
from listenbrainz.background.migrate_imports import FILE_MISSING_PROGRESS, migrate_imports
from listenbrainz.db import background
from listenbrainz.garage import delete_objects, ensure_bucket, get_garage_client, \
    get_user_data_import_bucket, list_object_names
from listenbrainz.metadata_cache.spotify.handler import SpotifyCrawlerHandler

from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver import db_conn


class ImportTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1850, "listens-import")
        db_user.agree_to_gdpr(self.db_conn, self.user["musicbrainz_id"])

    def tearDown(self):
        with self.app.app_context():
            client, bucket = self.get_import_storage()
            for error in delete_objects(client, bucket, list_object_names(client, bucket)):
                self.fail(f"Failed to remove import file {error.get('Key')}: {error.get('Message')}")
        super().tearDown()

    def get_import_storage(self):
        """ Get the garage client and the bucket the uploaded import files are stored in. """
        client = get_garage_client()
        bucket = get_user_data_import_bucket()
        ensure_bucket(client, bucket)
        return client, bucket

    def put_import_file(self, object_name, contents=b"import file contents"):
        """ Put a file in the import bucket, as if the webserver had uploaded it. """
        with self.app.app_context():
            client, bucket = self.get_import_storage()
            client.put_object(Bucket=bucket, Key=object_name, Body=contents)

    def list_import_files(self):
        with self.app.app_context():
            client, bucket = self.get_import_storage()
            return list_object_names(client, bucket)

    def create_zip(self, name, items: list[tuple[str, str]]) -> io.BytesIO:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for item in items:
                zf.write(item[0], item[1])
        buffer.seek(0)
        buffer.name = name
        return buffer

    def insert_sample_spotify_data(self):
        with open(self.path_to_data_file("spotify_cache_album.json"), "r") as f:
            data = json.load(f)
        album = SpotifyCrawlerHandler.transform_album(data)
        now = datetime.now(tz=timezone.utc)
        expires = now + timedelta(days=365)

        from listenbrainz.metadata_cache.store import insert
        insert(self.ts_conn.connection.cursor(), "spotify_cache", album, now, expires)
        self.ts_conn.connection.commit()

    def create_empty_zip(self):
        return self.create_zip("empty.zip", [])

    def create_spotify_zip(self):
        return self.create_zip("spotify.zip", [
            (
                self.path_to_data_file("spotify_streaming_2023.json"),
                "Spotify Extended Streaming History/Streaming_History_Audio_2023.json"
            ),
            (
                self.path_to_data_file("spotify_streaming_endsong_0.json"),
                "MyData/endsong_0.json"
            )
        ])

    def create_spotify_skipped_tracks_zip(self):
        return self.create_zip("spotify.zip", [
            (
                self.path_to_data_file("spotify_skipped_tracks.json"),
                "Spotify Extended Streaming History/Streaming_History_Audio_2023.json"
            )
        ])

    def create_listenbrainz_export_zip(self):
        return self.create_zip("listenbrainz_export.zip", [
            (
                self.path_to_data_file("listenbrainz_listens.jsonl"),
                "listens/2025/8.jsonl"
            )
        ])

    def create_listenbrainz_mixed_validity_zip(self):
        return self.create_zip("listenbrainz_mixed_validity.zip", [
            (
                self.path_to_data_file("listenbrainz_mixed_validity.jsonl"),
                "listens/2025/8.jsonl"
            )
        ])

    def create_listenbrainz_all_invalid_zip(self):
        return self.create_zip("listenbrainz_all_invalid.zip", [
            (
                self.path_to_data_file("listenbrainz_all_invalid.jsonl"),
                "listens/2025/8.jsonl"
            )
        ])

    def test_api_invalid_auth(self):
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={
                "service": "spotify",
                "file": self.create_empty_zip(),
            },
            content_type="multipart/form-data"
        )
        self.assert401(response)

        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={
                "service": "spotify",
                "file": self.create_empty_zip(),
            },
            headers={"Authorization": "Token invalidtoken"},
            content_type="multipart/form-data"
        )
        self.assert401(response)

        old_reject_setting = self.app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"]
        try:
            self.app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"] = True
            response = self.client.post(
                self.custom_url_for("import_listens_api_v1.create_import_task"),
                data={
                    "service": "spotify",
                    "file": self.create_empty_zip(),
                },
                headers={"Authorization": f"Token {self.user['auth_token']}"},
                content_type="multipart/form-data"
            )
            self.assert401(response)
        finally:
            self.app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"] = old_reject_setting

        db_user.pause(self.db_conn, self.user["id"])
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={
                "service": "spotify",
                "file": self.create_empty_zip(),
            },
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert401(response)

    def test_api_success(self):
        from_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        to_date = datetime.now(tz=timezone.utc)
        data = {
            "service": "spotify",
            "file": self.create_empty_zip(),
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)

        orig_data = response.json
        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=orig_data["import_id"]),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        data = response.json
        self.assertEqual(data["metadata"]["status"], "waiting")
        self.assertEqual(data["metadata"]["filename"], "empty.zip")
        self.assertEqual(data["service"], "spotify")
        self.assertEqual(datetime.fromisoformat(data["from_date"]), from_date)
        self.assertEqual(datetime.fromisoformat(data["to_date"]), to_date)

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.list_import_tasks"),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        data = response.json
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["import_id"], orig_data["import_id"])
        self.assertEqual(data[0]["service"], "spotify")
        self.assertEqual(data[0]["from_date"], from_date.isoformat())
        self.assertEqual(data[0]["to_date"], to_date.isoformat())
        self.assertEqual(data[0]["metadata"]["status"], "waiting")
        self.assertEqual(data[0]["metadata"]["filename"], "empty.zip")

        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.delete_import_task", import_id=orig_data["import_id"]),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        self.assertEqual([], self.list_import_files())

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.list_import_tasks"),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        data = response.json
        self.assertEqual(len(data), 0)

    def test_api_existing_import(self):
        from_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        to_date = datetime.now(tz=timezone.utc)
        data = {
            "service": "spotify",
            "file": self.create_empty_zip(),
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)

        data = {
            "service": "spotify",
            "file": self.create_empty_zip(),
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "An import task is already in progress!")

    def test_api_invalid_service(self):
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={"file": self.create_empty_zip(), "service": "invalidservice"},
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "This service is not supported!")

        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={"file": self.create_empty_zip()},
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "No service selected!")

    def test_invalid_date(self):
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={
                "service": "spotify",
                "file": self.create_empty_zip(),
                "from_date": "invaliddate"
            },
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid from_date format!")

        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={
                "service": "spotify",
                "file": self.create_empty_zip(),
                "to_date": "invaliddate"
            },
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid to_date format!")

    def test_invalid_service_file_combination(self):
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={
                "service": "spotify",
                "file": open(self.path_to_data_file("librefm.csv"), "rb"),
            },
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Only zip files are allowed for this service!")

        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data={
                "service": "librefm",
                "file": self.create_empty_zip(),
            },
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Only csv files are allowed for this service!")

    def test_file_path_attack(self):
        file = self.create_empty_zip()
        data = {
            "service": "spotify",
            "file": (file, "../etc/passwd.zip"),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        # the object name must not be able to escape the bucket's top level
        object_name = response.json["file_path"]
        self.assertNotIn("/", object_name)
        self.assertTrue(object_name.endswith("etc_passwd.zip"), object_name)
        self.assertEqual([object_name], self.list_import_files())

    def test_same_name_file_does_not_override(self):
        from_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        to_date = datetime.now(tz=timezone.utc)
        data = {
            "service": "spotify",
            "file": self.create_empty_zip(),
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)

        user2 = db_user.get_or_create(self.db_conn, 1851, "listens-import2")
        data = {
            "service": "spotify",
            "file": self.create_empty_zip(),
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user2['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)

        self.assertEqual(2, len(self.list_import_files()))

    def test_import_task_auth(self):
        from_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        to_date = datetime.now(tz=timezone.utc)
        data = {
            "service": "spotify",
            "file": self.create_empty_zip(),
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)

        import_id = response.json["import_id"]
        url = self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id)

        user2 = db_user.get_or_create(self.db_conn, 1851, "listens-import2")
        response = self.client.get(
            url,
            headers={"Authorization": f"Token {self.user2['auth_token']}"},
        )
        self.assert404(response)

        response = self.client.get(url)
        self.assert401(response)

        url = self.custom_url_for("import_listens_api_v1.delete_import_task", import_id=import_id)
        response = self.client.post(
            url,
            headers={"Authorization": f"Token {self.user2['auth_token']}"},
        )
        self.assert404(response)

        response = self.client.post(url)
        self.assert401(response)

    def test_import_spotify(self):
        self.insert_sample_spotify_data()
        data = {
            "service": "spotify",
            "file": self.create_spotify_zip(),
            "from_date": datetime(2015, 1, 1).isoformat(),
            "to_date": datetime(2024, 1, 1).isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        # Some tracks will be skipped,only expecting 6 tracks 
        response = self.wait_for_query_to_have_items(url, num_items=6, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 6)

        self.assertEqual(listens[0]["listened_at"], 1679250697)
        track_metadata = listens[0]["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "All Time Low, Demi Lovato, blackbear")
        self.assertEqual(track_metadata["track_name"], "Monsters (feat. Demi Lovato and blackbear)")
        self.assertEqual(track_metadata["release_name"], "Monsters (feat. Demi Lovato and blackbear)")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")
        self.assertEqual(additional_info["origin_url"], "https://open.spotify.com/track/50DMJJpAeQv4fIpxZvQz2e")
        self.assertEqual(additional_info["music_service"], "spotify.com")
        self.assertEqual(additional_info["spotify_album_id"], "https://open.spotify.com/album/1EGlv1JGCUPolWU4qv7bsK")

        # Verify validation stats are stored in metadata
        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertEqual(metadata["success_count"], 6)
        self.assertGreaterEqual(metadata["attempted_count"], 6)
    
    def test_skip_import_spotify(self):
        # Listens should get skipped for a variety of reasons (manually skipped, errors, etc.)
        data = {
            "service": "spotify",
            "file": self.create_spotify_skipped_tracks_zip(),
            "from_date": datetime(2012, 1, 1).isoformat(),
            "to_date": datetime(2024, 1, 1).isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        # all tracks except two will be skipped
        response = self.wait_for_query_to_have_items(url, num_items=2, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 2)

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertIn("detailed_message", metadata)
        # More tracks were attempted but filtered during processing
        self.assertEqual(metadata["success_count"], 2)
        self.assertEqual(metadata["attempted_count"], 15)
        self.assertEqual(metadata["detailed_message"], "Discarded: 12 manually skipped or interrupted, 1 incognito mode")


    def test_import_listenbrainz(self):
        data = {
            "service": "listenbrainz",
            "file": self.create_listenbrainz_export_zip(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=2, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 2)

        self.assertEqual(listens[0]["listened_at"], 1748967954)
        track_metadata = listens[0]["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "The Mamas & The Papas")
        self.assertEqual(track_metadata["track_name"], "California Dreamin'")
        self.assertEqual(track_metadata["release_name"], "If You Can Believe Your Eyes & Ears")
        self.assertNotIn("mbid_mapping", track_metadata)
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertEqual(metadata["attempted_count"], 2)
        self.assertEqual(metadata["success_count"], 2)

    def test_import_librefm(self):
        data = {
            "service": "librefm",
            "file": open(self.path_to_data_file("librefm.csv"), "rb")
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=3, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 3)

        self.assertEqual(listens[0]["listened_at"], 1704067200)
        track_metadata = listens[0]["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Oasis")
        self.assertEqual(track_metadata["track_name"], "Wonderwall")
        self.assertEqual(track_metadata["release_name"], "(What's the Story) Morning Glory?")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        self.assertEqual(listens[1]["listened_at"], 1690348225)
        track_metadata = listens[1]["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Sweet Garden")
        self.assertEqual(track_metadata["track_name"], "Altered State")
        self.assertNotIn("release_name", track_metadata)
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        self.assertEqual(listens[2]["listened_at"], 1690347960)
        track_metadata = listens[2]["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "The Horrors")
        self.assertEqual(track_metadata["track_name"], "New Ice Age")
        self.assertEqual(track_metadata["release_name"], "Primary Colours")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertEqual(metadata["attempted_count"], 3)
        self.assertEqual(metadata["success_count"], 3)

    def test_import_librefm_without_album_column(self):
        data = {
            "service": "librefm",
            "file": open(self.path_to_data_file("librefm_no_album_column.csv"), "rb"),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=2, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 2)

        first_listen = listens[0]
        self.assertEqual(first_listen["listened_at"], 1762874400)
        track_metadata = first_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Rick Astley")
        self.assertEqual(track_metadata["track_name"], "Never Gonna Give You Up")
        self.assertNotIn("release_name", track_metadata)
        self.assertEqual(track_metadata["additional_info"]["submission_client"], "ListenBrainz Archive Importer")

        second_listen = listens[1]
        self.assertEqual(second_listen["listened_at"], 1609459200)
        track_metadata = second_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Nina Simone")
        self.assertEqual(track_metadata["track_name"], "Feeling Good")
        self.assertNotIn("release_name", track_metadata)
        self.assertEqual(track_metadata["additional_info"]["submission_client"], "ListenBrainz Archive Importer")

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertEqual(metadata["attempted_count"], 2)
        self.assertEqual(metadata["success_count"], 2)

    def test_import_librefm_with_date_range(self):
        data = {
            "service": "librefm",
            "file": open(self.path_to_data_file("librefm.csv"), "rb"),
            "from_date": datetime(2023, 1, 1, tzinfo=timezone.utc).isoformat(),
            "to_date": datetime(2023, 12, 1, tzinfo=timezone.utc).isoformat(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=2, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 2)

        first_listen = listens[0]
        self.assertEqual(first_listen["listened_at"], 1690348225)
        track_metadata = first_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Sweet Garden")
        self.assertEqual(track_metadata["track_name"], "Altered State")
        self.assertNotIn("release_name", track_metadata)
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        second_listen = listens[1]
        self.assertEqual(second_listen["listened_at"], 1690347960)
        track_metadata = second_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "The Horrors")
        self.assertEqual(track_metadata["track_name"], "New Ice Age")
        self.assertEqual(track_metadata["release_name"], "Primary Colours")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertEqual(metadata["attempted_count"], 3)
        self.assertEqual(metadata["success_count"], 2)

    def test_import_librefm_via_maloja(self):
        data = {
            "service": "librefm",
            "file": open(self.path_to_data_file("librefm_via_maloja.csv"), "rb")
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=3, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 3)

        first_listen = listens[0]
        self.assertEqual(first_listen["listened_at"], 1760532855)
        track_metadata = first_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Vega Trails")
        self.assertEqual(track_metadata["track_name"], "Old Friend; The Sea")
        self.assertEqual(track_metadata["release_name"], "Sierra Tracks")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        second_listen = listens[1]
        self.assertEqual(second_listen["listened_at"], 1690348225)
        track_metadata = second_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Sweet Garden")
        self.assertEqual(track_metadata["track_name"], "Altered State")
        self.assertNotIn("release_name", track_metadata)
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        third_listen = listens[2]
        self.assertEqual(third_listen["listened_at"], 1690347960)
        track_metadata = third_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "The Horrors")
        self.assertEqual(track_metadata["track_name"], "New Ice Age")
        self.assertEqual(track_metadata["release_name"], "Primary Colours")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")
    
        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertEqual(metadata["attempted_count"], 3)
        self.assertEqual(metadata["success_count"], 3)

    def test_import_librefm_no_header(self):
        data = {
            "service": "librefm",
            "file": open(self.path_to_data_file("librefm_no_header.csv"), "rb")
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        import time
        for _ in range(20):
            r = self.client.get(
                self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
                headers={"Authorization": f"Token {self.user['auth_token']}"},
            )
            self.assert200(r)
            metadata = r.json["metadata"]
            if metadata["status"] in ["completed", "failed"]:
                break
            time.sleep(0.25)

        self.assertEqual(metadata["status"], "failed")
        self.assertEqual("Unable to locate Libre.fm header row in import file.", metadata["progress"])

    def test_import_librefm_with_comments(self):
        data = {
            "service": "librefm",
            "file": open(self.path_to_data_file("librefm_with_comments.csv"), "rb")
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=3, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 3)

        first_listen = listens[0]
        self.assertEqual(first_listen["listened_at"], 1760532855)
        track_metadata = first_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Vega Trails")
        self.assertEqual(track_metadata["track_name"], "Old Friend; The Sea")
        self.assertEqual(track_metadata["release_name"], "Sierra Tracks")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        second_listen = listens[1]
        self.assertEqual(second_listen["listened_at"], 1690348225)
        track_metadata = second_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Sweet Garden")
        self.assertEqual(track_metadata["track_name"], "Altered State")
        self.assertNotIn("release_name", track_metadata)
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        third_listen = listens[2]
        self.assertEqual(third_listen["listened_at"], 1690347960)
        track_metadata = third_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "The Horrors")
        self.assertEqual(track_metadata["track_name"], "New Ice Age")
        self.assertEqual(track_metadata["release_name"], "Primary Colours")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertEqual(metadata["attempted_count"], 3)
        self.assertEqual(metadata["success_count"], 3)

    def test_import_panoscrobbler(self):
        data = {
            "service": "panoscrobbler",
            "file": open(self.path_to_data_file("panoscrobbler.jsonl"), "rb"),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=2, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 2)


        self.assertEqual(listens[0]["listened_at"], 1762957898)
        track_metadata = listens[0]["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "KiloWatts")
        self.assertEqual(
            track_metadata["track_name"], "Scraped On The Way Out")
        self.assertEqual(track_metadata["release_name"], "Problem/Solving")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["album_artist_name"], "KiloWatts")
        self.assertEqual(
            additional_info["submission_client"], "PanoScrobbler Archive Importer")
        self.assertIn("media_player", additional_info)
        self.assertIn("media_player_version", additional_info)
        self.assertEqual(additional_info["duration_ms"], 346958)

        self.assertEqual(listens[1]["listened_at"], 1762874400)
        track_metadata = listens[1]["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Rick Astley")
        self.assertEqual(
            track_metadata["track_name"], "Never Gonna Give You Up")
        self.assertEqual(
            track_metadata["release_name"], "Whenever You Need Somebody")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["album_artist_name"], "Rick Astley")
        self.assertEqual(
            additional_info["submission_client"], "PanoScrobbler Archive Importer")
        self.assertIn("media_player", additional_info)
        self.assertIn("media_player_version", additional_info)
        self.assertEqual(additional_info["duration_ms"], 216000)

    def test_import_maloja(self):
        data = {
            "service": "maloja",
            "file": open(self.path_to_data_file("maloja.json"), "rb")
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=2, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 2)

        first_listen = listens[0]
        self.assertEqual(first_listen["listened_at"], 1760532855)
        track_metadata = first_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Vega Trails")
        self.assertEqual(track_metadata["track_name"], "Old Friend; The Sea")
        self.assertEqual(track_metadata["release_name"], "Sierra Tracks")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "Maloja Archive Importer")
        self.assertEqual(additional_info["original_submission_client"], "turntable")
        self.assertNotIn("duration", additional_info)
        self.assertEqual(additional_info["duration_played"], 245)

        second_listen = listens[1]
        self.assertEqual(second_listen["listened_at"], 1760532613)
        track_metadata = second_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Alabaster Deplume")
        self.assertEqual(track_metadata["track_name"], "Not Now, Jesus")
        self.assertEqual(track_metadata["release_name"], "To Cy & Lee: Instrumentals Vol. 1")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "Maloja Archive Importer")
        self.assertEqual(additional_info["original_submission_client"], "turntable")
        self.assertEqual(additional_info["duration"], 220)
        self.assertNotIn("duration_played", additional_info)

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertEqual(metadata["attempted_count"], 2)
        self.assertEqual(metadata["success_count"], 2)

    def test_import_maloja_empty(self):
        data = {
            "service": "maloja",
            "file": open(self.path_to_data_file("maloja_malformed.json"), "rb")
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        import time
        for _ in range(20):
            r = self.client.get(
                self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
                headers={"Authorization": f"Token {self.user['auth_token']}"},
            )
            self.assert200(r)
            metadata = r.json["metadata"]
            if metadata["status"] in ["completed", "failed"]:
                break
            time.sleep(0.25)

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        r = self.client.get(url)
        self.assert200(r)
        listens = r.json["payload"]["listens"]
        self.assertEqual(len(listens), 0)

        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertEqual(metadata["attempted_count"], 3)
        self.assertEqual(metadata["success_count"], 0)
        self.assertEqual(metadata["status"], "completed")

    def test_import_with_partial_validation_failures(self):
        data = {
            "service": "listenbrainz",
            "file": self.create_listenbrainz_mixed_validity_zip(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=3, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 3)

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)

        self.assertEqual(metadata["attempted_count"], 5)
    
        self.assertEqual(metadata["success_count"], 3)
    
        self.assertEqual(metadata["status"], "completed")

    def test_import_with_all_validation_failures(self):
        data = {
            "service": "listenbrainz",
            "file": self.create_listenbrainz_all_invalid_zip(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        for _ in range(20):
            response = self.client.get(
                self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
                headers={"Authorization": f"Token {self.user['auth_token']}"},
            )
            self.assert200(response)
            metadata = response.json["metadata"]
            if metadata["status"] in ["completed", "failed"]:
                break
            time.sleep(0.5)

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.client.get(url)
        self.assert200(response)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 0)

        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertEqual(metadata["attempted_count"], 3)
        self.assertEqual(metadata["success_count"], 0)
        self.assertEqual(metadata["status"], "completed")

    def test_validation_stats_initialized_on_import_start(self):
        data = {
            "service": "listenbrainz",
            "file": self.create_listenbrainz_export_zip(),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        
        self.assertIn("status", metadata)
        self.assertIn("progress", metadata)
        self.assertEqual(metadata["status"], "waiting")

    def test_unsupported_listens_importer_service(self):
        self.db_conn.execute(text("ALTER TYPE user_data_import_service_type ADD VALUE IF NOT EXISTS 'foobar'"))
        self.db_conn.commit()

        # create task without API so that we can use an unsupported service
        # can happen when background_tasks container is not updated in production
        # but web container is.
        result = background.create_import_task(
            self.db_conn,
            user_id=self.user["id"],
            service="foobar",
            from_date=datetime(2021, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
            file_path="xyz.zip",
            filename="xyz.zip",
        )
        self.db_conn.commit()

        metadata = None
        for _ in range(20):
            response = self.client.get(
                self.custom_url_for(
                    "import_listens_api_v1.get_import_task",
                    import_id=result["import_id"]
                ),
                headers={"Authorization": f"Token {self.user['auth_token']}"},
            )
            self.assert200(response)
            metadata = response.json["metadata"]
            if metadata["status"] in ["completed", "failed"]:
                break
            time.sleep(0.5)

        self.assertEqual(metadata["status"], "failed")
        self.assertEqual(metadata["progress"], "Unsupported service: foobar")

    def test_import_audioscrobbler(self):
        data = {
            "service": "audioscrobbler",
            "file": open(self.path_to_data_file(".scrobbler.log"), "rb"),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=2, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 2)

        first_listen = listens[0]
        self.assertEqual(first_listen["listened_at"], 1577840400)
        track_metadata = first_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "今堀恒雄")
        self.assertEqual(track_metadata["track_name"], "YELLOW ALERT")
        self.assertEqual(track_metadata["release_name"], "trigun the first donuts")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "Audioscrobbler Archive Importer")
        self.assertEqual(additional_info["original_submission_client"], "Rockbox sansae200")
        self.assertEqual(additional_info["duration"], 185)
        self.assertEqual(additional_info["tracknumber"], "18")
        self.assertNotIn("track_mbid", additional_info)

        second_listen = listens[1]
        self.assertEqual(second_listen["listened_at"], 1577836800)
        track_metadata = second_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "The Beatles")
        self.assertEqual(track_metadata["track_name"], "Come Together")
        self.assertEqual(track_metadata["release_name"], "Abbey Road")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "Audioscrobbler Archive Importer")
        self.assertEqual(additional_info["original_submission_client"], "Rockbox sansae200")
        self.assertEqual(additional_info["duration"], 259)
        self.assertEqual(additional_info["tracknumber"], "1")
        self.assertEqual(additional_info["track_mbid"], "d5e4fb56-e457-4684-aa31-63ce70ee5a8c")

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertEqual(metadata["attempted_count"], 3)
        self.assertEqual(metadata["success_count"], 2)

    def test_import_spinitron(self):
        data = {
            "service": "spinitron",
            "file": open(self.path_to_data_file("spinitron_sample.csv"), "rb"),
        }
        response = self.client.post(
            self.custom_url_for("import_listens_api_v1.create_import_task"),
            data=data,
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="multipart/form-data"
        )
        self.assert200(response)
        import_id = response.json["import_id"]

        url = self.custom_url_for("api_v1.get_listens", user_name=self.user["musicbrainz_id"])
        response = self.wait_for_query_to_have_items(url, num_items=3, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 3)

        first_listen = listens[0]
        self.assertEqual(first_listen["listened_at"], 1725523387)
        track_metadata = first_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Microdisney")
        self.assertEqual(track_metadata["track_name"], "People Just Want To Dream")
        self.assertEqual(track_metadata["release_name"], "Crooked Mile")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "Spinitron Archive Importer")
        self.assertEqual(additional_info["original_submission_client"], "spinitron")
        self.assertEqual(additional_info["label"], "UMC (Universal Music Catalogue)")

        second_listen = listens[1]
        self.assertEqual(second_listen["listened_at"], 1725523173)
        track_metadata = second_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Ganglians")
        self.assertEqual(track_metadata["track_name"], "Jungle")
        self.assertEqual(track_metadata["release_name"], "Still Living")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "Spinitron Archive Importer")
        self.assertEqual(additional_info["label"], "Souterrain Transmissions")

        third_listen = listens[2]
        self.assertEqual(third_listen["listened_at"], 1725522874)
        track_metadata = third_listen["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Kramer")
        self.assertEqual(track_metadata["track_name"], "Hello Music")
        self.assertEqual(track_metadata["release_name"], "The Guilt Trip")
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "Spinitron Archive Importer")
        self.assertEqual(additional_info["label"], "Shimmy Disc")

        response = self.client.get(
            self.custom_url_for("import_listens_api_v1.get_import_task", import_id=import_id),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
        )
        self.assert200(response)
        metadata = response.json["metadata"]
        self.assertIn("attempted_count", metadata)
        self.assertIn("success_count", metadata)
        self.assertEqual(metadata["attempted_count"], 5)
        self.assertEqual(metadata["success_count"], 3)


    def create_import_row(self, file_path, status="waiting", service="spotify"):
        """ Insert a user data import row directly, as if the file had been uploaded to disk. """
        result = self.db_conn.execute(text("""
            INSERT INTO user_data_import (user_id, service, from_date, to_date, file_path, metadata)
                 VALUES (:user_id, :service, :from_date, :to_date, :file_path, :metadata)
              RETURNING id
        """), {
            "user_id": self.user["id"],
            "service": service,
            "from_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "to_date": datetime.now(tz=timezone.utc),
            "file_path": file_path,
            "metadata": json.dumps({"status": status, "progress": "", "filename": os.path.basename(file_path)}),
        })
        self.db_conn.commit()
        return result.first().id

    def get_import_row(self, import_id):
        result = self.db_conn.execute(
            text("SELECT file_path, metadata FROM user_data_import WHERE id = :import_id"),
            {"import_id": import_id}
        )
        return result.first()

    def test_migrate_imports(self):
        upload_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, upload_dir, True)

        pending_name = "11111111-1111-1111-1111-111111111111-pending.zip"
        finished_name = "22222222-2222-2222-2222-222222222222-finished.zip"
        orphan_name = "33333333-3333-3333-3333-333333333333-orphan.zip"
        missing_name = "44444444-4444-4444-4444-444444444444-missing.zip"

        # the paths of imports created before the migration are absolute paths on disk
        pending_id = self.create_import_row(os.path.join(upload_dir, pending_name))
        finished_id = self.create_import_row(
            os.path.join(upload_dir, finished_name), status="completed", service="listenbrainz"
        )
        missing_id = self.create_import_row(os.path.join(upload_dir, missing_name), status="waiting", service="librefm")

        for name in (pending_name, finished_name, orphan_name):
            with open(os.path.join(upload_dir, name), "wb") as f:
                f.write(b"contents of " + name.encode())

        with self.app.app_context():
            client, bucket = self.get_import_storage()

            migrate_imports(db_conn, upload_dir, dry_run=True)
            self.assertEqual([], self.list_import_files())
            self.assertEqual("waiting", self.get_import_row(missing_id).metadata["status"])
            self.assertTrue(self.get_import_row(pending_id).file_path.startswith(upload_dir))

            migrate_imports(db_conn, upload_dir)

            # only the file of the import that has not run yet is uploaded
            self.assertEqual([pending_name], self.list_import_files())
            uploaded = client.get_object(Bucket=bucket, Key=pending_name)
            with uploaded["Body"] as body:
                self.assertEqual(b"contents of " + pending_name.encode(), body.read())

        # the on disk paths are rewritten to the object names
        self.assertEqual(pending_name, self.get_import_row(pending_id).file_path)
        self.assertEqual(finished_name, self.get_import_row(finished_id).file_path)

        # the import whose file is nowhere to be found cannot be run
        missing = self.get_import_row(missing_id)
        self.assertEqual("failed", missing.metadata["status"])
        self.assertEqual(FILE_MISSING_PROGRESS, missing.metadata["progress"])
        self.assertEqual("waiting", self.get_import_row(pending_id).metadata["status"])

        # source files are kept unless asked otherwise
        self.assertEqual({pending_name, finished_name, orphan_name}, set(os.listdir(upload_dir)))

        with self.app.app_context():
            # re-running does not upload again and removes the source files when asked to
            migrate_imports(db_conn, upload_dir, delete_source=True)
            self.assertEqual([pending_name], self.list_import_files())
        self.assertEqual([], os.listdir(upload_dir))

    def test_cleanup_import_files_removes_files_of_imports_that_will_not_run(self):
        """ An import that has run, been cancelled or failed leaves its uploaded file behind. """
        pending_name = "66666666-6666-6666-6666-666666666666-pending.zip"
        failed_name = "77777777-7777-7777-7777-777777777777-failed.zip"
        completed_name = "88888888-8888-8888-8888-888888888888-completed.zip"
        cancelled_name = "99999999-9999-9999-9999-999999999999-cancelled.zip"
        self.create_import_row(pending_name)
        self.create_import_row(failed_name, status="failed", service="listenbrainz")
        self.create_import_row(completed_name, status="completed", service="listenbrainz")
        self.create_import_row(cancelled_name, status="cancelled", service="listenbrainz")
        for name in (pending_name, failed_name, completed_name, cancelled_name):
            self.put_import_file(name)

        with self.app.app_context():
            # a file that was only just uploaded may belong to an import that is still being
            # created, it is left alone until it is old enough
            cleanup_import_files(db_conn)
            self.assertEqual(
                {pending_name, failed_name, completed_name, cancelled_name},
                set(self.list_import_files())
            )

            with mock.patch("listenbrainz.background.listens_importer.storage.IMPORT_FILE_MIN_AGE",
                            timedelta(minutes=-1)):
                cleanup_import_files(db_conn)
            self.assertEqual([pending_name], self.list_import_files())

    def test_migrate_imports_does_not_fail_imports_when_no_file_was_found(self):
        """ Pointing the migration at the wrong directory must not fail every pending import. """
        upload_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, upload_dir, True)

        missing_name = "55555555-5555-5555-5555-555555555555-missing.zip"
        missing_id = self.create_import_row(os.path.join(upload_dir, missing_name))

        with self.app.app_context():
            self.get_import_storage()

            migrate_imports(db_conn, upload_dir)
            self.assertEqual("waiting", self.get_import_row(missing_id).metadata["status"])

            # unless the operator confirms that this is expected
            migrate_imports(db_conn, upload_dir, mark_missing_failed=True)

        missing = self.get_import_row(missing_id)
        self.assertEqual("failed", missing.metadata["status"])
        self.assertEqual(FILE_MISSING_PROGRESS, missing.metadata["progress"])
