from __future__ import print_function
from redis import Redis
import redis
import time


_redis = None

def init_redis_connection(app, host, port):
    global _redis
    while True:
        try:
            _redis = Redis(host=host, port=port)
            _redis.ping()
            return
        except redis.exceptions.ConnectionError as e:
            app.logger.error("Couldn't connect to redis: {}".format(str(e)))
            app.logger.error("Trying again in 2 seconds...")
            time.sleep(2)
