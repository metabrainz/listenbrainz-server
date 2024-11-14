#!/usr/bin/python3

import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError
from listenbrainz.domain.lastfm import LastfmService
from listenbrainz.listens_importer.base import ListensImporter
from listenbrainz.listenstore import LISTEN_MINIMUM_DATE
from listenbrainz.webserver import create_app
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_IMPORT, \
    LISTEN_TYPE_PLAYING_NOW


class LastfmImporter(ListensImporter):

    def __init__(self):
        super(LastfmImporter, self).__init__(
            name='LastfmImporter',
            user_friendly_name="Last.fm",
            service=LastfmService(),
        )

    @staticmethod
    def convert_scrobble_to_listen(scrobble):
        """ Converts data retrieved from the last.fm API into a listen. """
        track_name = scrobble.get("name")
        track_mbid = scrobble.get("mbid")

        artist = scrobble.get("artist", {})
        artist_name = artist.get("#text")
        artist_mbid = artist.get("mbid")

        album = scrobble.get("album")
        album_name = album.get("#text")
        album_mbid = album.get("mbid")

        if "date" in scrobble:
            listened_at = int(scrobble["date"]["uts"])
            listen_type = LISTEN_TYPE_IMPORT
            listen = {"listened_at": listened_at}
        else:
            # todo: check now playing @attr
            listen_type = LISTEN_TYPE_PLAYING_NOW
            listen = {}

        if not track_name or not artist_name:
            return None, None

        track_metadata = {
            "artist_name": artist_name,
            "track_name": track_name,
        }
        if album_name:
            track_metadata["release_name"] = album_name

        additional_info = {
            "submission_client": "ListenBrainz lastfm importer v2"
        }
        if track_mbid:
            additional_info["lastfm_track_mbid"] = track_mbid
        if artist_mbid:
            additional_info["lastfm_artist_mbid"] = artist_mbid
        if album_mbid:
            additional_info["lastfm_release_mbid"] = album_mbid

        if additional_info:
            track_metadata["additional_info"] = additional_info

        listen["track_metadata"] = track_metadata
        return listen, listen_type


    def get_user_recent_tracks(self, session, user, page):
        """ Get user’s recently played tracks from last.fm api. """
        latest_listened_at = user["latest_listened_at"] or LISTEN_MINIMUM_DATE
        params = {
            "method": "user.getrecenttracks",
            "format": "json",
            "api_key": current_app.config["LASTFM_API_KEY"],
            "limit": 200,
            "user": user["external_user_id"],
            "from": int(latest_listened_at.timestamp()),
            "page": page
        }
        response = session.get(current_app.config["LASTFM_API_URL"], params=params)
        match response.status_code:
            case 200:
                return response.json()
            case 404:
                raise ExternalServiceError("Last.FM user with username %s not found" % (params["user"],))
            case 429:
                raise ExternalServiceError("Encountered a rate limit.")
            case _:
                raise ExternalServiceAPIError('Error from the lastfm API while getting listens: %s' % (str(response.text),))


    def process_one_user(self, user: dict) -> int:
        """ Get recently played songs for this user and submit them to ListenBrainz.

        Returns:
            the number of recently played listens imported for the user
        """
        try:
            imported_listen_count = 0
            session = requests.Session()
            session.mount(
                "https://",
                HTTPAdapter(max_retries=Retry(
                    total=3,
                    backoff_factor=1,
                    allowed_methods=["GET"],
                    # retry on 400 because last.fm wraps some service errors in 400 errors
                    status_forcelist=[400, 413, 429, 500, 502, 503, 504]
                ))
            )

            response = self.get_user_recent_tracks(session, user, page=1)
            pages = int(response["recenttracks"]["@attr"]["totalPages"])

            for page in range(pages, 0, -1):
                current_app.logger.info("Processing page %s", page)
                response = self.get_user_recent_tracks(session, user, page)
                now_playing_listen, listens, latest_listened_at = self.parse_and_validate_listen_items(
                    self.convert_scrobble_to_listen,
                    response["recenttracks"]["track"]
                )

                if now_playing_listen is not None:
                    self.submit_listens_to_listenbrainz(user, [now_playing_listen], listen_type=LISTEN_TYPE_PLAYING_NOW)
                    current_app.logger.info('imported now playing listen for %s' % (str(user['musicbrainz_id']),))
                    imported_listen_count += 1

                if listens:
                    self.submit_listens_to_listenbrainz(user, listens, listen_type=LISTEN_TYPE_IMPORT)
                    self.service.update_latest_listen_ts(user['user_id'], latest_listened_at)
                    current_app.logger.info('imported %d listens for %s' % (len(listens), str(user['musicbrainz_id'])))
                    imported_listen_count += len(listens)

            return imported_listen_count
        except ExternalServiceAPIError as e:
            # if it is an error from the Spotify API, show the error message to the user
            self.service.update_user_import_status(user_id=user['user_id'], error=str(e))
            if not current_app.config['TESTING']:
                self.notify_error(user['musicbrainz_id'], str(e))
            raise e

    def process_all_users(self):
        # todo: last.fm is prone to errors, especially for entire history imports. currently doing alternate passes
        #   where we ignore and reattempt
        result = super().process_all_users()
        self.exclude_error = not self.exclude_error
        return result


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        importer = LastfmImporter()
        importer.main()
