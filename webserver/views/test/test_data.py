from __future__ import absolute_import
from webserver.testing import ServerTestCase
from webserver.views import data
from webserver.external import musicbrainz
from flask import url_for


class DataViewsTestCase(ServerTestCase):

    def setUp(self):
        super(DataViewsTestCase, self).setUp()
        data.musicbrainz.get_recording_by_id = FakeMusicBrainz.get_recording_by_id

    def test_api(self):
        resp = self.client.get(url_for('data.api'))
        self.assertEqual(resp.status_code, 302)  # Should redirect to data page

    def test_data(self):
        resp = self.client.get(url_for('data.data'))
        self.assert200(resp)

    def test_view_low_level(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        resp = self.client.get(url_for('data.view_low_level', mbid=mbid))
        self.assertEqual(resp.status_code, 404)

        self.load_low_level_data(mbid)

        resp = self.client.get(url_for('data.view_low_level', mbid=mbid))
        self.assertEqual(resp.status_code, 200)

    def test_summary(self):
        mbid = '0dad432b-16cc-4bf0-8961-fd31d124b01b'
        resp = self.client.get(url_for('data.summary', mbid=mbid))
        self.assertEqual(resp.status_code, 404)

        self.load_low_level_data(mbid)

        resp = self.client.get(url_for('data.summary', mbid=mbid))
        self.assertEqual(resp.status_code, 200)

        # We don't have data for this recording, but it exists in MusicBrainz.
        resp = self.client.get(url_for('data.summary', mbid='770cc467-8dde-4d22-bc4c-a42f91e7515e'))
        self.assertEqual(resp.status_code, 404)
        self.assertIn("We don't have any information about this recording yet.",
                      resp.data.decode("utf-8"))


class FakeMusicBrainz(object):

    @staticmethod
    def get_recording_by_id(mbid):
        # Converting to string because `mbid` argument might be a UUID.
        if str(mbid) == "770cc467-8dde-4d22-bc4c-a42f91e7515e":
            return {
                "id": "770cc467-8dde-4d22-bc4c-a42f91e7515e",
                "title": "Never Gonna Give You Up",
                "artist-credit-phrase": "Rick Astley",
                "length": "212845",
                "artist-credit": [
                    {
                        "artist": {
                            "id": "db92a151-1ac2-438b-bc43-b82e149ddd50",
                            "name": "Rick Astley",
                            "sort-name": "Astley, Rick"
                        }
                    }
                ],
                "release-count": 155,
                "release-list": [
                    # incomplete, obviously
                    {
                        "barcode": "0035627152924",
                        "country": "GB",
                        "date": "1987-10-01",
                        "id": "bf9e91ea-8029-4a04-a26a-224e00a83266",
                        "medium-count": 1,
                        "medium-list": [
                            {
                                "format": "CD",
                                "position": "1",
                                "track-count": 10,
                                "track-list": [
                                    {
                                        "id": "5385553f-17a8-3838-9e47-d037555c3af7",
                                        "length": "215733",
                                        "number": "1",
                                        "position": "1",
                                        "title": "Never Gonna Give You Up",
                                        "track_or_recording_length": "215733"
                                    }
                                ]
                            }
                        ],
                        "quality": "normal",
                        "release-event-count": 1,
                        "release-event-list": [
                            {
                                "area": {
                                    "id": "8a754a16-0027-3a29-b6d7-2b40ea0481ed",
                                    "iso-3166-1-code-list": ["GB"],
                                    "name": "United Kingdom",
                                    "sort-name": "United Kingdom"
                                },
                                "date": "1987-10-01"
                            }
                        ],
                        "status": "Official",
                        "text-representation": {"language": "eng", "script": "Latn"},
                        "title": "Whenever You Need Somebody"
                    },
                ],
            }
        else:
            raise musicbrainz.DataUnavailable("say what")
