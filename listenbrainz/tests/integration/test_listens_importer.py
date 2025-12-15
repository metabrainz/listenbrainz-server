import io
import json
import os.path
import shutil
import time
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest import mock

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import background
from listenbrainz.metadata_cache.spotify.handler import SpotifyCrawlerHandler

from listenbrainz.tests.integration import ListenAPIIntegrationTestCase


class ImportTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1850, "listens-import")
        db_user.agree_to_gdpr(self.db_conn, self.user["musicbrainz_id"])

    def tearDown(self):
        shutil.rmtree(self.app.config["UPLOAD_FOLDER"], ignore_errors=True)
        super().tearDown()

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

        with mock.patch("listenbrainz.webserver.views.import_listens.mb_engine"):
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
        self.assertFalse(Path(orig_data["file_path"]).exists())

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
        self.assertTrue(
            os.path.abspath(response.json["file_path"])
            .startswith(self.app.config["UPLOAD_FOLDER"])
        )

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

        self.assertEqual(
            len(list(Path(self.app.config["UPLOAD_FOLDER"]).iterdir())),
            2
        )

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
        self.assertEqual(metadata["success_count"], 2)
        # More tracks were attempted but filtered during processing
        self.assertGreaterEqual(metadata["attempted_count"], 2)


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
        response = self.wait_for_query_to_have_items(url, num_items=2, attempts=20)
        listens = response.json["payload"]["listens"]
        self.assertEqual(len(listens), 2)

        self.assertEqual(listens[0]["listened_at"], 1690348225)
        track_metadata = listens[0]["track_metadata"]
        self.assertEqual(track_metadata["artist_name"], "Sweet Garden")
        self.assertEqual(track_metadata["track_name"], "Altered State")
        self.assertNotIn("release_name", track_metadata)
        additional_info = track_metadata["additional_info"]
        self.assertEqual(additional_info["submission_client"], "ListenBrainz Archive Importer")

        self.assertEqual(listens[1]["listened_at"], 1690347960)
        track_metadata = listens[1]["track_metadata"]
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
        self.assertEqual(metadata["attempted_count"], 2)
        self.assertEqual(metadata["success_count"], 2)

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
            save_path="xyz.zip",
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
