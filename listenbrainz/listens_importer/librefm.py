import time

from flask import current_app

from listenbrainz.domain.librefm import LibrefmService
from listenbrainz.listens_importer.lastfm import BaseLastfmImporter
from listenbrainz.webserver import create_app


class LibrefmImporter(BaseLastfmImporter):

    def __init__(self):
        super().__init__(
            name="LibreFmImporter",
            user_friendly_name="Libre.fm",
            service=LibrefmService(),
            api_key=current_app.config["LIBREFM_API_KEY"],
            api_base_url=current_app.config["LIBREFM_API_URL"],
        )

    def get_user_recent_tracks(self, session, user, page):
        time.sleep(1)
        return super().get_user_recent_tracks(session, user, page)

    def get_total_pages(self, session, user):
        response = super().get_user_recent_tracks(session, user, page=1)
        # when the user has not submitted any listens since the given timestamp
        # libre.fm returns the following error. on the other hand last.fm simply
        # returns an empty list of tracks and total pages as 0
        if "error" in response and response["error"]["code"] == "7":
            return 0
        return int(response["recenttracks"]["@attr"]["totalPages"])


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        importer = LibrefmImporter()
        importer.main()
