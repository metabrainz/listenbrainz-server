from brainzutils import cache
from troi.service import Service

import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats
from data.model.user_entity import EntityRecord
from listenbrainz.webserver import db_conn

STATS_CACHE_TTL = 3600  # 1 hour — stats update weekly/monthly


class LBRadioStatsService(Service):
    """Replaces the HTTP stats fetch in LBRadioStatsRecordingElement.

    Reads user recording stats from the DB directly instead of calling
    the HTTP API loopback.
    """

    SLUG = "stats"

    def __init__(self):
        super().__init__(self.SLUG)

    def fetch(self, user_name, time_range, offset):
        user = db_user.get_by_mb_id(db_conn, user_name)
        if user is None:
            raise RuntimeError(f"Cannot find user: {user_name}")

        cache_key = f"lb_radio_stats:{user['id']}:{time_range}"
        cached = cache.get(cache_key, decode=True)
        if cached is not None:
            return cached[offset:offset + 100]

        stats = db_stats.get(user["id"], "recordings", time_range, EntityRecord)
        if stats is None:
            raise RuntimeError(
                f"There are no stats available for user '{user_name}' for the {time_range} time_range."
            )

        recordings = []
        for r in stats.data.__root__:
            r = r.dict()
            if r.get("recording_mbid") is not None:
                recordings.append({
                    "recording_mbid": r["recording_mbid"],
                    "artist_mbids": r.get("artist_mbids") or [],
                })

        cache.set(cache_key, recordings, STATS_CACHE_TTL, encode=True)
        return recordings[offset:offset + 100]
