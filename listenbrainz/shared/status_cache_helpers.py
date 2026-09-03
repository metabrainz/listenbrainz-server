"""Shared cache helpers for service status data."""

from brainzutils import cache

STATUS_PREFIX = "listenbrainz.status"
STATS_TIMESTAMPS_CACHE_KEY = STATUS_PREFIX + ".stats-timestamps"


def get_stats_timestamps():
    return cache.get(STATS_TIMESTAMPS_CACHE_KEY)


def set_stats_timestamps(timestamps, expirein):
    cache.set(STATS_TIMESTAMPS_CACHE_KEY, timestamps, expirein)


def invalidate_stats_timestamps():
    cache.delete(STATS_TIMESTAMPS_CACHE_KEY)
