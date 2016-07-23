from redis import Redis
from listenstore.listenstore import RedisListenStore

_redis = None


def init_redis_connection(host):
    """Create a connection to the Redis server."""
    global _redis
    _redis = RedisListenStore({
        'REDIS_HOST': host,
    })
    return _redis
