from redis import Redis

_redis = None


def init_redis_connection(host):
    """Create a connection to the Redis server."""
    global _redis
    _redis = Redis(host)
