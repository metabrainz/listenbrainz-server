import time
from typing import Optional

from listenbrainz.listenstore import TimescaleListenStore

_ts: Optional[TimescaleListenStore] = None


def init_timescale_connection(app):
    global _ts

    if not app.config.get("SQLALCHEMY_TIMESCALE_URI"):
        return

    while True:
        try:
            _ts = TimescaleListenStore(app.logger)
            break
        except Exception:
            app.logger.error(f"Couldn't create TimescaleListenStore instance (sleeping and trying again...):", exc_info=True)
            time.sleep(2)

    return _ts
