import musicbrainzngs
from musicbrainzngs.musicbrainz import ResponseError
from messybrainz.cache import _redis

CACHE_TIMEOUT = 86400  # 1 day


def get_recording_by_id(mbid):
    recording = cache.get(mbid)
    if not recording:
        try:
            recording = musicbrainzngs.get_recording_by_id(mbid, includes=['artists', 'releases', 'media'])['recording']
        except ResponseError as e:
            raise DataUnavailable(e)
    _redis.setex(mbid, recording, CACHE_TIMEOUT)
    return recording


class DataUnavailable(Exception):
    pass
