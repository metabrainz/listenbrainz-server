import time
from typing import Optional

from listenbrainz.db import listens as listens_db
from listenbrainz.listenstore import TimescaleListenStore

_ts: Optional[TimescaleListenStore] = None


def init_timescale_connection(app):
    global _ts

    # LISTENSTORE_UP takes the listenstore offline for maintenance, the decorators in
    # listenbrainz.webserver.decorators then turn requests that need it away
    if not app.config["LISTENSTORE_UP"]:
        app.logger.warning("Not creating TimescaleListenStore instance, the listenstore is marked down")
        return

    if not listens_db.engine:
        app.logger.error("Cannot create TimescaleListenStore instance, listens database engine not initialized")
        return

    while True:
        try:
            _ts = TimescaleListenStore(app.logger)
            break
        except Exception:
            app.logger.error(f"Couldn't create TimescaleListenStore instance (sleeping and trying again...):", exc_info=True)
            time.sleep(2)

    return _ts
