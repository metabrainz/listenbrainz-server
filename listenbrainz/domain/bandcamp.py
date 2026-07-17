from listenbrainz.db import bandcamp as db_bandcamp
from listenbrainz.domain.subsonic import SubsonicService


class BandcampService(SubsonicService):
    """Subsonic-compatible Bandcamp service connection."""

    service_name = "Bandcamp"
    db = db_bandcamp
    encryption_config_key = "BANDCAMP_ENCRYPTION_KEY"
    default_instance_url = "https://bandcamp.com/api/subsonic"
