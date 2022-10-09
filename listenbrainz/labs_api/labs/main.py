#!/usr/bin/env python3

from datasethoster.main import create_app, init_sentry, register_query
from listenbrainz.labs_api.labs.api.artist_country_from_artist_mbid import ArtistCountryFromArtistMBIDQuery
from listenbrainz.labs_api.labs.api.artist_credit_from_artist_mbid import ArtistCreditIdFromArtistMBIDQuery
from listenbrainz.labs_api.labs.api.recording_from_recording_mbid import RecordingFromRecordingMBIDQuery
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery
from listenbrainz.labs_api.labs.api.explain_mbid_mapping import ExplainMBIDMappingQuery
from listenbrainz.labs_api.labs.api.recording_search import RecordingSearchQuery
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery
from listenbrainz.labs_api.labs.api.spotify_metadata_lookup import SpotifyIdFromMetadataQuery
from listenbrainz.webserver import load_config

register_query(ArtistCountryFromArtistMBIDQuery())
register_query(ArtistCreditIdFromArtistMBIDQuery())
register_query(RecordingFromRecordingMBIDQuery())
register_query(MBIDMappingQuery())
register_query(ExplainMBIDMappingQuery())
register_query(RecordingSearchQuery())
register_query(ArtistCreditRecordingLookupQuery())
register_query(SpotifyIdFromMetadataQuery())

app = create_app()
load_config(app)
init_sentry(app, "DATASETS_SENTRY_DSN")
