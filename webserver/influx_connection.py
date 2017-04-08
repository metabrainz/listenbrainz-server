from listenstore import InfluxListenStore

_influx = None

def init_influx_connection(conf):
    global _influx
    _influx = InfluxListenStore(conf)
    return _influx
