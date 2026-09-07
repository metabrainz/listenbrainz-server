from unittest.mock import patch

import flask_testing
from datasethoster import RequestSource
from datasethoster.main import create_app

from listenbrainz.labs_api.labs.api.spotify import SpotifyIdFromMBIDOutput
from listenbrainz.labs_api.labs.api.metadata_index.metadata_index_from_mbid_lookup import MetadataIdFromMBIDInput
from listenbrainz.labs_api.labs.api.spotify.spotify_mbid_lookup import SpotifyIdFromMBIDQuery

url_rel_mbids = [
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "cccccccc-cccc-cccc-cccc-cccccccccccc",
]

url_rel_db_response = [
    ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", ["2nLtzopw4rPReszdYBJU6h"]),
    ("cccccccc-cccc-cccc-cccc-cccccccccccc", ["5HCyWlXZPP0y6Gqq8TgA20", "3KkXRkHbMCARz0aVfEt68P"]),
]

fetch_params = [
    MetadataIdFromMBIDInput(recording_mbid="11111111-1111-1111-1111-111111111111"),
    MetadataIdFromMBIDInput(recording_mbid="22222222-2222-2222-2222-222222222222"),
    MetadataIdFromMBIDInput(recording_mbid="33333333-3333-3333-3333-333333333333"),
    MetadataIdFromMBIDInput(recording_mbid="44444444-4444-4444-4444-444444444444"),
]


def make_base_fetch_results():
    """Build a fresh list each call so in-place mutations don't leak between tests."""
    return [
        SpotifyIdFromMBIDOutput(
            recording_mbid="11111111-1111-1111-1111-111111111111",
            artist_name="Artist One",
            release_name="Album One",
            track_name="Track One",
            spotify_track_ids=["6rqhFgbbKwnb9MLmUQDhG6"],
        ),
        SpotifyIdFromMBIDOutput(
            recording_mbid="22222222-2222-2222-2222-222222222222",
            artist_name="Artist Two",
            release_name="Album Two",
            track_name="Track Two",
            spotify_track_ids=[],
        ),
        SpotifyIdFromMBIDOutput(
            recording_mbid="33333333-3333-3333-3333-333333333333",
            artist_name="Artist Three",
            release_name="Album Three",
            track_name="Track Three",
            spotify_track_ids=[],
        ),
    ]


url_rel_fallback = {
    "22222222-2222-2222-2222-222222222222": ["0VjIjW4GlUZAMYd2vXMi4a"],
    "44444444-4444-4444-4444-444444444444": ["3KkXRkHbMCARz0aVfEt68P"],
}

URL_RELS_PATCH = 'listenbrainz.labs_api.labs.api.spotify.spotify_mbid_lookup.lookup_spotify_track_ids_from_mb_url_rels'
SUPER_FETCH_PATCH = 'listenbrainz.labs_api.labs.api.metadata_index.metadata_index_from_mbid_lookup.MetadataIndexFromMBIDQuery.fetch'


class MainTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_app()
        app.config['MB_DATABASE_URI'] = 'yermom'
        app.config['SQLALCHEMY_TIMESCALE_URI'] = 'yermom'
        return app

    def setUp(self):
        self.maxDiff = None
        flask_testing.TestCase.setUp(self)

    def tearDown(self):
        flask_testing.TestCase.tearDown(self)

    def test_basics(self):
        q = SpotifyIdFromMBIDQuery()
        self.assertEqual(q.names()[0], "spotify-id-from-mbid")
        self.assertEqual(q.names()[1], "Spotify Track ID Lookup using recording mbid")
        self.assertNotEqual(q.introduction(), "")
        self.assertCountEqual(q.inputs().__fields__.keys(), ['recording_mbid'])
        self.assertCountEqual(q.outputs().__fields__.keys(), [
            'recording_mbid', 'artist_name', 'release_name', 'track_name', 'spotify_track_ids'
        ])

    @patch('listenbrainz.labs_api.labs.api.utils.execute_values')
    @patch('psycopg2.connect')
    def test_url_rels_returns_matching_mbids(self, mock_connect, mock_execute_values):
        mock_connect().__enter__().cursor().__enter__().fetchall.return_value = url_rel_db_response

        from listenbrainz.labs_api.labs.api.utils import lookup_spotify_track_ids_from_mb_url_rels
        result = lookup_spotify_track_ids_from_mb_url_rels(url_rel_mbids)

        self.assertEqual(result, {
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa": ["2nLtzopw4rPReszdYBJU6h"],
            "cccccccc-cccc-cccc-cccc-cccccccccccc": ["5HCyWlXZPP0y6Gqq8TgA20", "3KkXRkHbMCARz0aVfEt68P"],
        })
        self.assertNotIn("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", result)

    @patch('listenbrainz.labs_api.labs.api.utils.execute_values')
    @patch('psycopg2.connect')
    def test_url_rels_empty_input(self, mock_connect, mock_execute_values):
        from listenbrainz.labs_api.labs.api.utils import lookup_spotify_track_ids_from_mb_url_rels
        result = lookup_spotify_track_ids_from_mb_url_rels([])

        self.assertEqual(result, {})
        mock_connect.assert_not_called()

    @patch('listenbrainz.labs_api.labs.api.utils.execute_values')
    @patch('psycopg2.connect')
    def test_url_rels_no_matches(self, mock_connect, mock_execute_values):
        mock_connect().__enter__().cursor().__enter__().fetchall.return_value = []

        from listenbrainz.labs_api.labs.api.utils import lookup_spotify_track_ids_from_mb_url_rels
        result = lookup_spotify_track_ids_from_mb_url_rels(url_rel_mbids)

        self.assertEqual(result, {})

    @patch('listenbrainz.labs_api.labs.api.utils.execute_values')
    @patch('psycopg2.connect')
    def test_url_rels_filters_null_track_ids(self, mock_connect, mock_execute_values):
        mock_connect().__enter__().cursor().__enter__().fetchall.return_value = [
            ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", [None]),
            ("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", ["2nLtzopw4rPReszdYBJU6h", None]),
        ]

        from listenbrainz.labs_api.labs.api.utils import lookup_spotify_track_ids_from_mb_url_rels
        result = lookup_spotify_track_ids_from_mb_url_rels(url_rel_mbids)

        self.assertNotIn("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", result)
        self.assertEqual(result["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"], ["2nLtzopw4rPReszdYBJU6h"])

    @patch(URL_RELS_PATCH, return_value=url_rel_fallback)
    @patch(SUPER_FETCH_PATCH)
    def test_fallback_updates_existing_rows(self, mock_super_fetch, mock_url_rels):
        mock_super_fetch.return_value = make_base_fetch_results()

        q = SpotifyIdFromMBIDQuery()
        results = q.fetch(fetch_params, RequestSource.json_post)

        result_by_mbid = {str(r.recording_mbid): r for r in results}

        self.assertEqual(
            result_by_mbid["11111111-1111-1111-1111-111111111111"].spotify_track_ids,
            ["6rqhFgbbKwnb9MLmUQDhG6"]
        )
        self.assertEqual(
            result_by_mbid["22222222-2222-2222-2222-222222222222"].spotify_track_ids,
            ["0VjIjW4GlUZAMYd2vXMi4a"]
        )
        self.assertEqual(result_by_mbid["22222222-2222-2222-2222-222222222222"].artist_name, "Artist Two")

    @patch(URL_RELS_PATCH, return_value=url_rel_fallback)
    @patch(SUPER_FETCH_PATCH)
    def test_fallback_creates_new_row_for_dropped_mbid(self, mock_super_fetch, mock_url_rels):
        mock_super_fetch.return_value = make_base_fetch_results()

        q = SpotifyIdFromMBIDQuery()
        results = q.fetch(fetch_params, RequestSource.json_post)

        result_by_mbid = {str(r.recording_mbid): r for r in results}

        self.assertIn("44444444-4444-4444-4444-444444444444", result_by_mbid)
        self.assertEqual(
            result_by_mbid["44444444-4444-4444-4444-444444444444"].spotify_track_ids,
            ["3KkXRkHbMCARz0aVfEt68P"]
        )
        self.assertIsNone(result_by_mbid["44444444-4444-4444-4444-444444444444"].artist_name)

    @patch(URL_RELS_PATCH, return_value=url_rel_fallback)
    @patch(SUPER_FETCH_PATCH)
    def test_fallback_leaves_unmatched_recordings_unchanged(self, mock_super_fetch, mock_url_rels):
        mock_super_fetch.return_value = make_base_fetch_results()

        q = SpotifyIdFromMBIDQuery()
        results = q.fetch(fetch_params, RequestSource.json_post)

        result_by_mbid = {str(r.recording_mbid): r for r in results}

        self.assertEqual(
            result_by_mbid["33333333-3333-3333-3333-333333333333"].spotify_track_ids,
            []
        )

    @patch(URL_RELS_PATCH, return_value={})
    @patch(SUPER_FETCH_PATCH)
    def test_fallback_no_url_rel_matches(self, mock_super_fetch, mock_url_rels):
        mock_super_fetch.return_value = make_base_fetch_results()

        q = SpotifyIdFromMBIDQuery()
        results = q.fetch(fetch_params, RequestSource.json_post)

        self.assertEqual(len(results), len(make_base_fetch_results()))
        for r in results:
            if str(r.recording_mbid) == "11111111-1111-1111-1111-111111111111":
                self.assertEqual(r.spotify_track_ids, ["6rqhFgbbKwnb9MLmUQDhG6"])
            else:
                self.assertEqual(r.spotify_track_ids, [])

    @patch(URL_RELS_PATCH)
    @patch(SUPER_FETCH_PATCH)
    def test_all_resolved_skips_fallback(self, mock_super_fetch, mock_url_rels):
        all_resolved = [
            SpotifyIdFromMBIDOutput(
                recording_mbid="11111111-1111-1111-1111-111111111111",
                artist_name="Artist One",
                release_name="Album One",
                track_name="Track One",
                spotify_track_ids=["6rqhFgbbKwnb9MLmUQDhG6"],
            ),
        ]
        mock_super_fetch.return_value = all_resolved
        params = [MetadataIdFromMBIDInput(recording_mbid="11111111-1111-1111-1111-111111111111")]

        q = SpotifyIdFromMBIDQuery()
        results = q.fetch(params, RequestSource.json_post)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].spotify_track_ids, ["6rqhFgbbKwnb9MLmUQDhG6"])
        mock_url_rels.assert_not_called()

    @patch(URL_RELS_PATCH)
    @patch(SUPER_FETCH_PATCH, return_value=[])
    def test_empty_params(self, mock_super_fetch, mock_url_rels):
        q = SpotifyIdFromMBIDQuery()
        results = q.fetch([], RequestSource.json_post)

        self.assertEqual(results, [])
        mock_url_rels.assert_not_called()
