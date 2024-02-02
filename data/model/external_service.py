from enum import Enum


class ExternalServiceType(Enum):
    SPOTIFY = 'spotify'
    CRITIQUEBRAINZ = 'critiquebrainz'
    # this type only exists for historical purposes and matching urls in the profile endpoint
    MUSICBRAINZ = 'musicbrainz'
    LASTFM = 'lastfm'
    LIBREFM = 'librefm'
    SOUNDCLOUD = 'soundcloud'
    APPLE = 'apple'
    # these are not MB deployments but LB deployments
    MUSICBRAINZ_PROD = 'musicbrainz-prod'
    MUSICBRAINZ_BETA = 'musicbrainz-beta'
    MUSICBRAINZ_TEST = 'musicbrainz-test'
