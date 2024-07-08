#!/usr/bin/env python3
import psycopg2.extras
from datasethoster.main import create_app, init_sentry, register_query

from listenbrainz.labs_api.labs.api.apple.apple_mbid_lookup import AppleMusicIdFromMBIDQuery
from listenbrainz.labs_api.labs.api.apple.apple_metadata_lookup import AppleMusicIdFromMetadataQuery
from listenbrainz.labs_api.labs.api.artist_country_from_artist_mbid import ArtistCountryFromArtistMBIDQuery
from listenbrainz.labs_api.labs.api.artist_credit_from_artist_mbid import ArtistCreditIdFromArtistMBIDQuery
from listenbrainz.labs_api.labs.api.artist_credit_recording_release_lookup import \
    ArtistCreditRecordingReleaseLookupQuery
from listenbrainz.labs_api.labs.api.mbid_mapping_release import MBIDMappingReleaseQuery
from listenbrainz.labs_api.labs.api.recording_from_recording_mbid import RecordingFromRecordingMBIDQuery
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery
from listenbrainz.labs_api.labs.api.explain_mbid_mapping import ExplainMBIDMappingQuery
from listenbrainz.labs_api.labs.api.recording_search import RecordingSearchQuery
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery
from listenbrainz.labs_api.labs.api.similar_artists import SimilarArtistsViewerQuery
from listenbrainz.labs_api.labs.api.similar_recordings import SimilarRecordingsViewerQuery
from listenbrainz.labs_api.labs.api.soundcloud.soundcloud_from_mbid_lookup import SoundCloudIdFromMBIDQuery
from listenbrainz.labs_api.labs.api.soundcloud.soundcloud_from_metadata_lookup import SoundCloudIdFromMetadataQuery
from listenbrainz.labs_api.labs.api.spotify.spotify_mbid_lookup import SpotifyIdFromMBIDQuery
from listenbrainz.labs_api.labs.api.spotify.spotify_metadata_lookup import SpotifyIdFromMetadataQuery
from listenbrainz.labs_api.labs.api.user_listen_sessions import UserListensSessionQuery
from listenbrainz.labs_api.labs.api.tag_similarity import TagSimilarityQuery
from listenbrainz.labs_api.labs.api.bulk_tag_lookup import BulkTagLookup
from listenbrainz.webserver import load_config
from listenbrainz import db
from listenbrainz.db import timescale as ts

register_query(ArtistCountryFromArtistMBIDQuery())
register_query(ArtistCreditIdFromArtistMBIDQuery())
register_query(RecordingFromRecordingMBIDQuery())
register_query(MBIDMappingQuery())
register_query(MBIDMappingReleaseQuery())
register_query(ExplainMBIDMappingQuery())
register_query(RecordingSearchQuery())
register_query(ArtistCreditRecordingLookupQuery())
register_query(ArtistCreditRecordingReleaseLookupQuery())
register_query(SpotifyIdFromMetadataQuery())
register_query(SpotifyIdFromMBIDQuery())
register_query(AppleMusicIdFromMBIDQuery())
register_query(AppleMusicIdFromMetadataQuery())
register_query(SoundCloudIdFromMBIDQuery())
register_query(SoundCloudIdFromMetadataQuery())
register_query(UserListensSessionQuery())
register_query(SimilarRecordingsViewerQuery())
register_query(SimilarArtistsViewerQuery())
register_query(TagSimilarityQuery())
register_query(BulkTagLookup())

app = create_app()
load_config(app)
init_sentry(app, "DATASETS_SENTRY_DSN")
db.init_db_connection(app.config['SQLALCHEMY_DATABASE_URI'])
ts.init_db_connection(app.config['SQLALCHEMY_TIMESCALE_URI'])
psycopg2.extras.register_uuid()
