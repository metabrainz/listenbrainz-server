from troi.service import Service

import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
from listenbrainz.webserver import db_conn


class LBRadioRecsService(Service):
    """Replaces the paginated liblistenbrainz HTTP calls in LBRadioRecommendationRecordingElement.

    Returns the full raw recommendations list so the element applies its
    mode-based offset and listened filter directly, without HTTP pagination.
    """

    SLUG = "recs"

    def __init__(self):
        super().__init__(self.SLUG)

    def fetch(self, user_name: str) -> list[dict] | None:
        user = db_user.get_by_mb_id(db_conn, user_name)
        if user is None:
            return None

        recommendations = db_recommendations_cf_recording.get_user_recommendation(db_conn, user["id"])
        if recommendations is None:
            return None

        return recommendations.recording_mbid.dict().get("raw") or []
