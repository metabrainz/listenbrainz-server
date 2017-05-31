import musicbrainzngs
from musicbrainzngs.musicbrainz import ResponseError
from brainzutils import cache

CACHE_TIMEOUT = 86400  # 1 day


def get_recording_by_id(mbid):
    recording = cache.get(mbid)
    if not recording:
        try:
            recording = musicbrainzngs.get_recording_by_id(mbid, includes=['artists', 'releases', 'media'])['recording']
        except ResponseError as e:
            raise DataUnavailable(e)
    cache.set(mbid, recording, time=CACHE_TIMEOUT)
    return recording


class DataUnavailable(Exception):
    pass
