import logging

ORDER_DESC = 0
ORDER_ASC = 1
ORDER_TEXT = [ "DESC", "ASC" ]
DEFAULT_LISTENS_PER_FETCH = 25

LISTENS_DUMP_SCHEMA_VERSION = 1

REDIS_USER_TIMESTAMPS = "user.%s.timestamps" # substitute user_name
USER_CACHE_TIME = 3600 # in seconds. 1 hour

from listenbrainz.listenstore import listenstore
import listenbrainz.listen as listen
ListenStore = listenstore.ListenStore
Listen = listen.Listen


# Certain modules configure logging on a module-level context, so we have to
# configure logging as early as possible or some loggers will be disabled by
# reconfiguring logging.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')


from listenbrainz.listenstore import redis_listenstore
from listenbrainz.listenstore import influx_listenstore
from listenbrainz.listenstore import timescale_listenstore
RedisListenStore = redis_listenstore.RedisListenStore
InfluxListenStore = influx_listenstore.InfluxListenStore
TimescaleListenStore = timescale_listenstore.TimescaleListenStore
