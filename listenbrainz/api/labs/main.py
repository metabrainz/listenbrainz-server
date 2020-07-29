#!/usr/bin/env python3

from datasethoster.main import app, register_query
from listenbrainz.api.labs.api.artist_country_from_artist_mbid import ArtistCountryFromArtistMBIDQuery
from listenbrainz.api.labs.api.artist_credit_from_artist_mbid_query import ArtistCreditIdFromArtistMBIDQuery
from listenbrainz.webserver import load_config

register_query(ArtistCountryFromArtistMBIDQuery())
register_query(ArtistCreditIdFromArtistMBIDQuery())

load_config(app)

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=4201)
