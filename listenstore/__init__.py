import logging

MIN_ID = 1033430400     # approx when audioscrobbler was created
ORDER_DESC = 0
ORDER_ASC = 1
ORDER_TEXT = [ "DESC", "ASC" ]
DEFAULT_LISTENS_PER_FETCH = 25

REDIS_USER_TIMESTAMPS = "user.%s.timestamps" # substitute user_name
USER_CACHE_TIME = 3600 # in seconds. 1 hour

import listenstore
import listen
ListenStore = listenstore.ListenStore
Listen = listen.Listen


# Certain modules configure logging on a module-level context, so we have to
# configure logging as early as possible or some loggers will be disabled by
# reconfiguring logging.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')


import postgres_listenstore
import redis_listenstore
import influx_listenstore
PostgresListenStore = postgres_listenstore.PostgresListenStore
RedisListenStore = redis_listenstore.RedisListenStore
InfluxListenStore = influx_listenstore.InfluxListenStore
