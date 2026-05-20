#!/usr/bin/env python3
import psycopg2.extras
from brainzutils import cache
from datasethoster.main import create_app, init_sentry, register_query

from listenbrainz.labs_api.labs.api.apple.apple_mbid_lookup import AppleMusicIdFromMBIDQuery
from listenbrainz.labs_api.labs.api.apple.apple_metadata_lookup import AppleMusicIdFromMetadataQuery
from listenbrainz.labs_api.labs.api.artist_country_from_artist_mbid import ArtistCountryFromArtistMBIDQuery
from listenbrainz.labs_api.labs.api.artist_credit_from_artist_mbid import ArtistCreditIdFromArtistMBIDQuery
from listenbrainz.labs_api.labs.api.artist_credit_recording_release_lookup import \
    ArtistCreditRecordingReleaseLookupQuery
from listenbrainz.labs_api.labs.api.recording_from_recording_mbid import RecordingFromRecordingMBIDQuery
from listenbrainz.labs_api.labs.api.recording_search import RecordingSearchQuery
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery
from listenbrainz.labs_api.labs.api.similar_artists import SimilarArtistsViewerQuery
from listenbrainz.labs_api.labs.api.similar_recordings.listens import SimilarRecordingsViewerQuery
from listenbrainz.labs_api.labs.api.similar_recordings.mlhd import MlhdSimilarRecordingsViewerQuery
from listenbrainz.labs_api.labs.api.soundcloud.soundcloud_from_mbid_lookup import SoundCloudIdFromMBIDQuery
from listenbrainz.labs_api.labs.api.soundcloud.soundcloud_from_metadata_lookup import SoundCloudIdFromMetadataQuery
from listenbrainz.labs_api.labs.api.spotify.spotify_mbid_lookup import SpotifyIdFromMBIDQuery
from listenbrainz.labs_api.labs.api.spotify.spotify_metadata_lookup import SpotifyIdFromMetadataQuery
from listenbrainz.labs_api.labs.api.user_listen_sessions import UserListensSessionQuery
from listenbrainz.labs_api.labs.api.tag_similarity import TagSimilarityQuery
from listenbrainz.labs_api.labs.api.bulk_tag_lookup import BulkTagLookup
from sqlalchemy.pool import QueuePool

from listenbrainz.webserver import load_config
from listenbrainz import db
from listenbrainz.db import timescale as ts

register_query(ArtistCountryFromArtistMBIDQuery())
register_query(ArtistCreditIdFromArtistMBIDQuery())
register_query(RecordingFromRecordingMBIDQuery())
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
register_query(MlhdSimilarRecordingsViewerQuery())
register_query(SimilarArtistsViewerQuery())
register_query(TagSimilarityQuery())
register_query(BulkTagLookup())

app = create_app()
load_config(app)
init_sentry(app, "DATASETS_SENTRY_DSN")
# labs_api uwsgi runs single-threaded workers (no `threads = N`), so each
# worker only needs one connection at a time per backend. Small pools keep
# pgbouncer client churn low without holding many idle slots.
db.init_db_connection(
    app.config["SQLALCHEMY_DATABASE_URI"],
    poolclass=QueuePool,
    pool_size=2,
    max_overflow=2,
    pool_pre_ping=True,
)
ts.init_db_connection(
    app.config["SQLALCHEMY_TIMESCALE_PGBOUNCER_URI"],
    poolclass=QueuePool,
    pool_size=2,
    max_overflow=2,
    pool_pre_ping=True,
)
cache.init(
    host=app.config["REDIS_HOST"],
    port=app.config["REDIS_PORT"],
    namespace=app.config["REDIS_NAMESPACE"]
)
psycopg2.extras.register_uuid()
