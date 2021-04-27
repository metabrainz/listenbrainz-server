#!/usr/bin/env python3

from datasethoster.main import create_app, init_sentry, register_query
from listenbrainz.labs_api.labs.api.artist_country_from_artist_mbid import ArtistCountryFromArtistMBIDQuery
from listenbrainz.labs_api.labs.api.artist_credit_from_artist_mbid import ArtistCreditIdFromArtistMBIDQuery
from listenbrainz.labs_api.labs.api.artist_credit_from_artist_msid import ArtistCreditIdFromArtistMSIDQuery
from listenbrainz.labs_api.labs.api.recording_from_recording_mbid import RecordingFromRecordingMBIDQuery
from listenbrainz.webserver import load_config

register_query(ArtistCountryFromArtistMBIDQuery())
register_query(ArtistCreditIdFromArtistMBIDQuery())
register_query(ArtistCreditIdFromArtistMSIDQuery())
register_query(RecordingFromRecordingMBIDQuery())

app = create_app()
load_config(app)
init_sentry(app, "DATASETS_SENTRY_DSN")
