import time
from listenbrainz.listenstore import InfluxListenStore

_influx = None

def init_influx_connection(logger, conf):
    global _influx
    while True:
        try:
            _influx = InfluxListenStore(conf, logger)
            break
        except Exception as e:
            logger.error("Couldn't create InfluxListenStore instance: {}, sleeping and trying again...".format(str(e)), exc_info=True)
            time.sleep(2)

    logger.info("Successfully created InfluxListenStore instance!")
    return _influx
