import time
from listenbrainz.listenstore import TimescaleListenStore

_ts = None


def init_timescale_connection(logger, conf):
    global _ts

    if not conf["SQLALCHEMY_TIMESCALE_URI"]:
        return

    while True:
        try:
            _ts = TimescaleListenStore(conf, logger)
            break
        except Exception as e:
            logger.error("Couldn't create TimescaleListenStore instance: {}, sleeping and trying again..."
                         .format(str(e)), exc_info=True)
            time.sleep(2)

    return _ts
