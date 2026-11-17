import inspect
import unittest
from unittest.mock import Mock, patch

from datasethoster.main import create_app, json_query_handler, registered_queries
from flask import Flask
import requests.exceptions
import typesense.exceptions

from listenbrainz.labs_api.labs.api.recording_search import RecordingSearchQuery
from listenbrainz.labs_api.labs.errors import init_error_handlers as init_labs_error_handlers
from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper
from listenbrainz.mbid_mapping_writer.typesense_utils import TypesenseUnavailable
from listenbrainz.webserver.errors import init_error_handlers
from listenbrainz.webserver.views import feedback_api, metadata_api


OUTAGES = (
    requests.exceptions.ConnectionError,
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ReadTimeout,
    typesense.exceptions.Timeout,
    typesense.exceptions.ServerError,
    typesense.exceptions.ServiceUnavailable,
    typesense.exceptions.HTTPStatus0Error,
    typesense.exceptions.TypesenseClientError,
)


class TypesenseUnavailableTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        init_error_handlers(self.app)
        # Exercise the actual view and error handler without Redis rate limiting.
        self.app.add_url_rule('/1/metadata/lookup/', view_func=inspect.unwrap(metadata_api.get_mbid_mapping))
        self.app.add_url_rule('/1/feedback/import', view_func=inspect.unwrap(feedback_api.import_feedback),
                              methods=['POST'])
        self.client = self.app.test_client()

    def test_navidrome_outages_abort_import_without_writing_feedback(self):
        tagged_song = {'artist': 'Artist', 'title': 'Tagged Track', 'musicBrainzId': 'recording-mbid'}
        untagged_song = {'artist': 'Artist', 'title': 'Track'}
        nav_user = {'instance_url': 'https://navidrome.example', 'md5_auth_token': 'token',
                    'salt': 'salt', 'username': 'user'}
        with patch.object(feedback_api, 'validate_auth_header', return_value={'id': 1}), \
                patch.object(feedback_api.NavidromeService, 'get_user', return_value=nav_user), \
                patch('listenbrainz.domain.navidrome.requests.get') as get, \
                patch('listenbrainz.domain.navidrome.db_feedback.bulk_insert_loved_tracks') as insert, \
                patch('typesense.documents.Documents.search') as search:
            get.return_value.json.return_value = {
                'subsonic-response': {'status': 'ok', 'starred': {'song': [tagged_song, untagged_song]}}}
            for error in OUTAGES:
                with self.subTest(error=error):
                    search.side_effect = error('private backend details')
                    response = self.client.post('/1/feedback/import', json={'service': 'navidrome'})
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.json['code'], 503)
                    self.assertNotIn('private backend details', response.json['error'])
                    insert.assert_not_called()

    def test_navidrome_tagged_tracks_do_not_need_typesense(self):
        nav_user = {'instance_url': 'https://navidrome.example', 'md5_auth_token': 'token',
                    'salt': 'salt', 'username': 'user'}
        with patch.object(feedback_api, 'validate_auth_header', return_value={'id': 1}), \
                patch.object(feedback_api.NavidromeService, 'get_user', return_value=nav_user), \
                patch('listenbrainz.domain.navidrome.requests.get') as get, \
                patch('listenbrainz.domain.navidrome.db_conn', new=Mock()), \
                patch('listenbrainz.domain.navidrome.db_feedback.bulk_insert_loved_tracks') as insert, \
                patch('typesense.documents.Documents.search') as search:
            get.return_value.json.return_value = {
                'subsonic-response': {'status': 'ok', 'starred': {'song': [
                    {'artist': 'Artist', 'title': 'Track', 'musicBrainzId': 'recording-mbid'}]}}}
            search.side_effect = requests.exceptions.ConnectionError('Typesense unavailable')
            response = self.client.post('/1/feedback/import', json={'service': 'navidrome'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {'total_found': 1, 'total_mapped': 1, 'total_imported': 1})
            insert.assert_called_once()
            search.assert_not_called()

    @patch.object(metadata_api, 'validate_auth_header')
    @patch.object(metadata_api.ArtistCreditRecordingLookupQuery, 'fetch', return_value=[])
    @patch('typesense.documents.Documents.search')
    def test_metadata_outages_return_503(self, search, exact, auth):
        for error in OUTAGES:
            with self.subTest(error=error):
                search.side_effect = error('private backend details')
                response = self.client.get('/1/metadata/lookup/?artist_name=Artist&recording_name=Track')
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json['code'], 503)
                self.assertNotIn('private backend details', response.json['error'])

    @patch.object(metadata_api, 'validate_auth_header')
    @patch.object(metadata_api.ArtistCreditRecordingLookupQuery, 'fetch')
    @patch('typesense.documents.Documents.search')
    def test_exact_match_does_not_need_typesense(self, search, exact, auth):
        match = {'recording_mbid': 'recording', 'release_mbid': 'release', 'artist_mbids': [],
                 'recording_name': 'Track', 'release_name': 'Album', 'artist_credit_name': 'Artist'}
        exact.return_value = [Mock(dict=Mock(return_value=match))]
        response = self.client.get('/1/metadata/lookup/?artist_name=Artist&recording_name=Track')
        self.assertEqual(response.status_code, 200)
        search.assert_not_called()

    @patch.object(metadata_api, 'validate_auth_header')
    @patch.object(metadata_api.ArtistCreditRecordingLookupQuery, 'fetch', return_value=[])
    @patch('typesense.documents.Documents.search', return_value={'hits': []})
    def test_no_match_remains_successful(self, search, exact, auth):
        response = self.client.get('/1/metadata/lookup/?artist_name=Artist&recording_name=Track')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {})

    @patch('listenbrainz.mbid_mapping_writer.mbid_mapper.sleep')
    @patch('typesense.documents.Documents.search', side_effect=requests.exceptions.ReadTimeout)
    def test_request_does_not_retry_read_timeout(self, search, sleep):
        with self.app.test_request_context('/'):
            mapper = MBIDMapper()
            with self.assertRaises(TypesenseUnavailable):
                mapper.lookup('collection', 'query')
        search.assert_called_once()
        sleep.assert_not_called()

    @patch('typesense.documents.Documents.search')
    def test_labs_outages_and_recovery(self, search):
        app = create_app()
        app.config['TESTING'] = True
        init_labs_error_handlers(app)
        app.add_url_rule('/recording-search/json', view_func=json_query_handler, methods=['GET', 'POST'])
        client = app.test_client()
        with patch.dict(registered_queries, {'recording-search': RecordingSearchQuery()}):
            for method in ('GET', 'POST'):
                for error in OUTAGES:
                    with self.subTest(method=method, error=error):
                        search.side_effect = error('private backend details')
                        kwargs = {'query_string': {'query': 'Artist Track'}} if method == 'GET' else {
                            'json': [{'query': 'Artist Track'}]}
                        response = client.open('/recording-search/json', method=method, **kwargs)
                        self.assertEqual(response.status_code, 503)
                        self.assertEqual(response.json['code'], 503)
                        self.assertEqual(response.headers['Cache-Control'], 'no-store')
                        self.assertNotIn('private backend details', response.json['error'])
                        search.side_effect = None
                        search.return_value = {'hits': []}
                        response = client.open('/recording-search/json', method=method, **kwargs)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json, [])
