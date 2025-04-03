from datetime import datetime, timezone

ORDER_DESC = 0
ORDER_ASC = 1
ORDER_TEXT = [ "DESC", "ASC" ]
DEFAULT_LISTENS_PER_FETCH = 25

# Schema version for the public listens dump, this should be updated
# when the format of the json document in the public dumps changes
LISTENS_DUMP_SCHEMA_VERSION = 1

LISTEN_MINIMUM_DATE = datetime(2002, 10, 1, tzinfo=timezone.utc)
# October 2002 is date before which most Last.FM data is rubbish
#: The minimum acceptable value for listened_at field
LISTEN_MINIMUM_TS = int(LISTEN_MINIMUM_DATE.timestamp())

# ╭∩╮
from listenbrainz.listenstore.redis_listenstore import RedisListenStore
from listenbrainz.listenstore.timescale_listenstore import TimescaleListenStore
