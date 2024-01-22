from enum import Enum


class ExternalServiceType(Enum):
    SPOTIFY = 'spotify'
    CRITIQUEBRAINZ = 'critiquebrainz'
    MUSICBRAINZ = 'musicbrainz'
    LASTFM = 'lastfm'
    LIBREFM = 'librefm'
    SOUNDCLOUD = 'soundcloud'
    APPLE = 'apple'
    # these are not MB deployments but LB deployments
    MUSICBRAINZ_PROD = 'musicbrainz-prod'
    MUSICBRAINZ_BETA = 'musicbrainz-beta'
    MUSICBRAINZ_TEST = 'musicbrainz-test'
