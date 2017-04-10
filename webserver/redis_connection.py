from redis import Redis
from listenstore import RedisListenStore

_redis = None

def init_redis_connection(host, port):
    """Create a connection to the Redis server."""
    global _redis
    _redis = RedisListenStore({
        'REDIS_HOST': host,
        'REDIS_PORT': port
    })
    return _redis
