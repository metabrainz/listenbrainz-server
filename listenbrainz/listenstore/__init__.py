ORDER_DESC = 0
ORDER_ASC = 1
ORDER_TEXT = [ "DESC", "ASC" ]
DEFAULT_LISTENS_PER_FETCH = 25

# Schema version for the public listens dump, this should be updated
# when the format of the json document in the public dumps changes
LISTENS_DUMP_SCHEMA_VERSION = 1

from listenbrainz.listenstore import listenstore
import listenbrainz.listen as listen
ListenStore = listenstore.ListenStore
Listen = listen.Listen


# ╭∩╮
from listenbrainz.listenstore import redis_listenstore
from listenbrainz.listenstore import timescale_listenstore
RedisListenStore = redis_listenstore.RedisListenStore
TimescaleListenStore = timescale_listenstore.TimescaleListenStore
