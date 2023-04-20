from enum import Enum


class ExternalServiceType(Enum):
    SPOTIFY = 'spotify'
    CRITIQUEBRAINZ = 'critiquebrainz'
    MUSICBRAINZ = 'musicbrainz'
    LASTFM = 'lastfm'
    LIBREFM = 'librefm'
