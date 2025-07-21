import json
import os
import io
import time
import zipfile
from io import BytesIO

import listenbrainz.db.user as db_user

from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver import db_conn


class ImportTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1799, 'suvid-import')
        db_user.agree_to_gdpr(self.db_conn, self.user['musicbrainz_id'])

        self.spotify_valid_listens = '''[
            {
                "ts": "2024-11-10T21:40:50Z",
                "platform": "windows",
                "ms_played": 234858,
                "conn_country": "IN",
                "ip_addr": "123.123.123.123",
                "master_metadata_track_name": "Nazrein Milaana Nazrein Churaana",
                "master_metadata_album_artist_name": "Benny Dayal",
                "master_metadata_album_album_name": "Jaane Tu... Ya Jaane Na",
                "spotify_track_uri": "spotify:track:3wnahgmj1q8YvjkoXTLG8c",
                "episode_name": null,
                "episode_show_name": null,
                "spotify_episode_uri": null,
                "audiobook_title": null,
                "audiobook_uri": null,
                "audiobook_chapter_uri": null,
                "audiobook_chapter_title": null,
                "reason_start": "clickrow",
                "reason_end": "trackdone",
                "shuffle": true,
                "skipped": false,
                "offline": false,
                "offline_timestamp": 1731274614,
                "incognito_mode": false
            },
            {
                "ts": "2024-12-20T16:46:47Z",
                "platform": "windows",
                "ms_played": 357067,
                "conn_country": "IN",
                "ip_addr": "123.123.123.123",
                "master_metadata_track_name": "Bulleya",
                "master_metadata_album_artist_name": "Vishal-Shekhar",
                "master_metadata_album_album_name": "Sultan",
                "spotify_track_uri": "spotify:track:3tgdOveYac7YMEAQD9sGLf",
                "episode_name": null,
                "episode_show_name": null,
                "spotify_episode_uri": null,
                "audiobook_title": null,
                "audiobook_uri": null,
                "audiobook_chapter_uri": null,
                "audiobook_chapter_title": null,
                "reason_start": "clickrow",
                "reason_end": "trackdone",
                "shuffle": false,
                "skipped": false,
                "offline": false,
                "offline_timestamp": 1734712847,
                "incognito_mode": false
            }
        ]'''

        self.spotify_valid_listens_zip = self.create_zip(self.spotify_valid_listens)
        self.spotify_invalid_listens = self.create_invalid_file()
    
    def post_listens(self, listens_file, service):
        data = {
            'file': (listens_file, "listens.zip"),
        }
        if service:
            data['service'] = service
        response = self.client.post(
            self.custom_url_for('api_v1.import'),
            data=data,
            content_type='multipart/form-data'
        )
        time.sleep(1)
        return response
    
    def post_empty(self):
        data = {
            'service': "spotify",
        }
        response = self.client.post(
            self.custom_url_for('import.create_import_task'),
            data=data,
            content_type='multipart/form-data'
        )
        time.sleep(1)
        return response
    

    def test_imports(self):
        self.temporary_login(self.user['login_id'])

        response = self.post_listens(self.spotify_valid_listens_zip, "spotify")
        self.assert200(response)

        response = self.post_listens(self.spotify_invalid_listens, "spotify")
        self.assert400(response)

        response = self.post_listens(self.spotify_valid_listens_zip, "abc")
        self.assert400(response)

        response = self.post_listens(self.spotify_valid_listens_zip, "")
        self.assert400(response)

        response = self.post_empty()
        self.assert400(response)

         





    def create_zip(self, filename="Spotify_Streaming_History.json", zipname="Spotify_Streaming_History.zip"):
        json_bytes = self.spotify_valid_listens.encode('utf-8')
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, json_bytes)
        zip_buffer.seek(0)
        zip_buffer.name = "Spotify_Streaming_History.zip"
        return zip_buffer

    def create_invalid_file(self):
        invalid_txt = io.BytesIO(b"Test")
        invalid_txt.name = "invalid.txt"
        return invalid_txt

