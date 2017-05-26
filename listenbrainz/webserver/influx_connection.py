from listenbrainz.listenstore import InfluxListenStore

_influx = None

def init_influx_connection(logger, conf):
    global _influx
    while True:
        try:
            _influx = InfluxListenStore(conf)
            break
        except Exception as e:
            logger.error("Couldn't create InfluxListenStore instance: {}".format(str(e)))
            logger.error("Sleeping 2 seconds and then retrying...")
            time.sleep(2)

    logger.info("Successfully created InfluxListenStore instance!")
    return _influx
