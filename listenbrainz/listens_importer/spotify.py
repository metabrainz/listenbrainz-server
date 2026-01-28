#!/usr/bin/python3

import time

import spotipy
from dateutil import parser
from flask import current_app
from spotipy import SpotifyException

from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError, \
    ExternalServiceInvalidGrantError
from listenbrainz.domain.spotify import SpotifyService

from listenbrainz.listens_importer.base import ListensImporter
from listenbrainz.webserver import create_app
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_IMPORT, LISTEN_TYPE_PLAYING_NOW


class SpotifyImporter(ListensImporter):

    def __init__(self):
        super(SpotifyImporter, self).__init__(
            name='spotify_reader',
            user_friendly_name="Spotify",
            service=SpotifyService(),
        )

    @staticmethod
    def _convert_spotify_play_to_listen(play, listen_type):
        """ Converts data retrieved from the Spotify API into a listen.

        Args:
            play (dict): a dict that represents a listen retrieved from Spotify
                , this should be an "item" from the spotify response.
            listen_type: the type of the listen (import or playing_now)

        Returns:
            listen (dict): dict that can be submitted to ListenBrainz
        """
        if listen_type == LISTEN_TYPE_PLAYING_NOW:
            track = play
            listen = {}
        else:
            track = play['track']
            listen = {
                'listened_at': parser.parse(play['played_at']).timestamp(),
            }

        if track is None:
            return None

        artists = track.get('artists', [])
        artist_names = []
        spotify_artist_ids = []
        for a in artists:
            name = a.get('name')
            if name is not None:
                artist_names.append(name)
            spotify_id = a.get('external_urls', {}).get('spotify')
            if spotify_id is not None:
                spotify_artist_ids.append(spotify_id)
        artist_name = ', '.join(artist_names)

        album = track.get('album', {})
        album_artists = album.get('artists', [])
        release_artist_names = []
        spotify_album_artist_ids = []
        for a in album_artists:
            name = a.get('name')
            if name is not None:
                release_artist_names.append(name)
            spotify_id = a.get('external_urls', {}).get('spotify')
            if spotify_id is not None:
                spotify_album_artist_ids.append(spotify_id)
        album_artist_name = ', '.join(release_artist_names)

        additional = {
            'tracknumber': track.get('track_number'),
            'spotify_artist_ids': spotify_artist_ids,
            'artist_names': artist_names,
            'discnumber': track.get('disc_number'),
            'duration_ms': track.get('duration_ms'),
            'spotify_album_id': album.get('external_urls', {}).get('spotify'),
            # Named 'release_*' because 'release_name' is an official name in the docs
            'release_artist_name': album_artist_name,
            'release_artist_names': release_artist_names,
            # Named 'album_*' because Spotify calls it album and this is spotify-specific
            'spotify_album_artist_ids': spotify_album_artist_ids,
            'submission_client': 'listenbrainz',
            'music_service': 'spotify.com'
        }
        isrc = track.get('external_ids', {}).get('isrc')
        spotify_url = track.get('external_urls', {}).get('spotify')
        if isrc:
            additional['isrc'] = isrc
        if spotify_url:
            additional['spotify_id'] = spotify_url
            additional['origin_url'] = spotify_url

        listen['track_metadata'] = {
            'artist_name': artist_name,
            'track_name': track['name'],
            'release_name': album['name'],
            'additional_info': additional,
        }
        return listen, listen_type

    def convert_spotify_current_play_to_listen(self, play):
        return self._convert_spotify_play_to_listen(play, LISTEN_TYPE_PLAYING_NOW)

    def convert_spotify_recent_play_to_listen(self, play):
        return self._convert_spotify_play_to_listen(play, LISTEN_TYPE_IMPORT)

    def make_api_request(self, user: dict, endpoint: str, **kwargs):
        """ Make an request to the Spotify API for particular user at specified endpoint with args.

        Args:
            user: the user whose plays are to be imported.
            endpoint: the name of Spotipy function which makes request to the required API endpoint

        Returns:
            the response from the spotify API

        Raises:
            ExternalServiceAPIError: if we encounter errors from the Spotify API.
            ExternalServiceError: if we encounter a rate limit, even after retrying.
        """
        retries = 10
        delay = 1
        tried_to_refresh_token = False

        while retries > 0:
            try:
                spotipy_client = spotipy.Spotify(auth=user['access_token'])
                spotipy_call = getattr(spotipy_client, endpoint)
                recently_played = spotipy_call(**kwargs)
                return recently_played
            except (AttributeError, TypeError):
                current_app.logger.critical("Invalid spotipy endpoint or arguments:", exc_info=True)
                return None
            except SpotifyException as e:
                retries -= 1
                if e.http_status == 429:
                    # Rate Limit Problems -- the client handles these, but it can still give up
                    # after a certain number of retries, so we look at the header and try the
                    # request again, if the error is raised
                    try:
                        time_to_sleep = int(e.headers.get('Retry-After', delay))
                    except ValueError:
                        time_to_sleep = delay
                    current_app.logger.warning('Encountered a rate limit, sleeping %d seconds and trying again...',
                                               time_to_sleep)
                    time.sleep(time_to_sleep)
                    delay += 1
                    if retries == 0:
                        raise ExternalServiceError('Encountered a rate limit.')

                elif e.http_status in (400, 403):
                    current_app.logger.critical('Error from the Spotify API for user %s: %s', user['musicbrainz_id'],
                                                str(e), exc_info=True)
                    raise ExternalServiceAPIError('Error from the Spotify API while getting listens: %s', str(e))
                elif e.http_status >= 500 and e.http_status < 600:
                    # these errors are not our fault, most probably. so just log them and retry.
                    current_app.logger.error('Error while trying to get listens for user %s: %s',
                                             user['musicbrainz_id'], str(e), exc_info=True)
                    if retries == 0:
                        raise ExternalServiceAPIError('Error from the spotify API while getting listens: %s', str(e))

                elif e.http_status == 401:
                    # if we get 401 Unauthorized from Spotify, that means our token might have expired.
                    # In that case, try to refresh the token, if there is an error even while refreshing
                    # give up and report to the user.
                    # We only try to refresh the token once, if we still get 401 after that, we give up.
                    if not tried_to_refresh_token:
                        user = SpotifyService().refresh_access_token(user['user_id'], user['refresh_token'])
                        tried_to_refresh_token = True

                    else:
                        raise ExternalServiceAPIError(
                            'Could not authenticate with Spotify, please unlink and link your account again.')
                elif e.http_status == 404:
                    current_app.logger.error("404 while trying to get listens for user %s", str(user), exc_info=True)
                    if retries == 0:
                        raise ExternalServiceError("404 while trying to get listens for user %s" % str(user))
            except Exception as e:
                retries -= 1
                current_app.logger.error('Unexpected error while getting listens: %s', str(e), exc_info=True)
                if retries == 0:
                    raise ExternalServiceError('Unexpected error while getting listens: %s' % str(e))

    def get_user_recently_played(self, user):
        """ Get tracks from the current user’s recently played tracks. """
        latest_listened_at_ts = 0
        if user['latest_listened_at']:
            latest_listened_at_ts = int(user['latest_listened_at'].timestamp() * 1000)  # latest listen UNIX ts in ms

        return self.make_api_request(user, 'current_user_recently_played', limit=50, after=latest_listened_at_ts)

    def get_user_currently_playing(self, user):
        """ Get the user's currently playing track.
        """
        return self.make_api_request(user, 'current_user_playing_track')

    def process_one_user(self, user: dict) -> int:
        """ Get recently played songs for this user and submit them to ListenBrainz.

        Args:
            user (spotify.Spotify): the user whose plays are to be imported.

        Raises:
            spotify.SpotifyAPIError: if we encounter errors from the Spotify API.
            spotify.SpotifyListenBrainzError: if we encounter a rate limit, even after retrying.
                                              or if we get errors while submitting the data to ListenBrainz
        Returns:
            the number of recently played listens imported for the user
        """
        try:
            if self.service.user_oauth_token_has_expired(user):
                user = self.service.refresh_access_token(user['user_id'], user['refresh_token'])

            listens = []
            latest_listened_at = None

            # If there is no playback, currently_playing will be None.
            # There are two playing types, track and episode. We use only the
            # track type. Therefore, when the user's playback type is not a track,
            # Spotify will set the item field to null which becomes None after
            # parsing the JSON. Due to these reasons, we cannot simplify the
            # checks below.
            currently_playing = self.get_user_currently_playing(user)
            if currently_playing is not None:
                currently_playing_item = currently_playing.get('item', None)
                if currently_playing_item is not None:
                    current_app.logger.debug('Received a currently playing track for %s', str(user))
                    now_playing_listen, _, _ = self.parse_and_validate_listen_items(
                        self.convert_spotify_current_play_to_listen,
                        [currently_playing_item]
                    )
                    if now_playing_listen:
                        self.submit_listens_to_listenbrainz(user, [now_playing_listen], listen_type=LISTEN_TYPE_PLAYING_NOW)

            recently_played = self.get_user_recently_played(user)
            if recently_played is not None and 'items' in recently_played:
                _, listens, latest_listened_at = self.parse_and_validate_listen_items(
                    self.convert_spotify_recent_play_to_listen,
                    recently_played['items']
                )
                current_app.logger.debug('Received %d tracks for %s', len(listens), str(user))

            # if we don't have any new listens, return. we don't check whether the listens list is empty here
            # because it will empty in both cases where we don't receive any listens and when we receive only
            # bad listens. so instead we check latest_listened_at which is None only in case when we received
            # nothing from spotify.
            if latest_listened_at is None:
                self.service.update_user_import_status(user['user_id'])
                return 0

            self.submit_listens_to_listenbrainz(user, listens, listen_type=LISTEN_TYPE_IMPORT)

            # we've succeeded so update the last_updated and latest_listened_at field for this user
            self.service.update_latest_listen_ts(user['user_id'], latest_listened_at)

            current_app.logger.info('imported %d listens for %s' % (len(listens), str(user['musicbrainz_id'])))
            return len(listens)

        except ExternalServiceInvalidGrantError:
            error_message = "It seems like you've revoked permission for us to read your spotify account"
            self.service.update_user_import_status(user_id=user['user_id'], error=error_message)
            if not current_app.config['TESTING']:
                self.notify_error(user['musicbrainz_id'], error_message)
            # user has revoked authorization through spotify ui or deleted their spotify account etc.
            #
            # we used to remove spotify access tokens from our database whenever we detected token revocation
            # at one point. but one day spotify had a downtime while resulted in false revocation errors, and
            # we ended up deleting most of our users' spotify access tokens. now we don't remove the token from
            # database. this is actually more resilient and without downsides. if a user actually revoked their
            # token, then its useless anyway so doesn't matter if we remove it. and if it is a false revocation
            # error, we are saved! :) in any case, we do set an error message for the user in the database
            # so that we can skip in future runs and notify them to reconnect if they want.
            raise ExternalServiceError("User has revoked spotify authorization")

        except ExternalServiceAPIError as e:
            # if it is an error from the Spotify API, show the error message to the user
            self.service.update_user_import_status(user_id=user['user_id'], error=str(e))
            if not current_app.config['TESTING']:
                self.notify_error(user['musicbrainz_id'], str(e))
            raise ExternalServiceError("Could not refresh user token from spotify")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        importer = SpotifyImporter()
        importer.main()
