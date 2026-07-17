from listenbrainz.db import navidrome as db_navidrome
from listenbrainz.domain.subsonic import SubsonicService


class NavidromeService(SubsonicService):
    """Subsonic-compatible Navidrome service connection."""

    service_name = "Navidrome"
    db = db_navidrome
    encryption_config_key = "NAVIDROME_ENCRYPTION_KEY"
