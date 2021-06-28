#!/usr/bin/python3
import time

import spotipy
from brainzutils import metrics

import listenbrainz.webserver

from listenbrainz.utils import safely_import_config
safely_import_config()

from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError, \
    ExternalServiceInvalidGrantError
from listenbrainz.domain.spotify import SpotifyService

from listenbrainz.webserver.errors import APIBadRequest

from dateutil import parser
from flask import current_app, render_template
from listenbrainz.webserver.views.api_tools import insert_payload, validate_listen, LISTEN_TYPE_IMPORT, LISTEN_TYPE_PLAYING_NOW
from listenbrainz.db import user as db_user
from listenbrainz.db.exceptions import DatabaseException
from spotipy import SpotifyException
from werkzeug.exceptions import InternalServerError, ServiceUnavailable
from brainzutils.mail import send_mail
from brainzutils.musicbrainz_db import editor as mb_editor

METRIC_UPDATE_INTERVAL = 60  # seconds
_listens_imported_since_start = 0
_metric_submission_time = time.monotonic() + METRIC_UPDATE_INTERVAL

def notify_error(musicbrainz_id: str, error: str):
    """ Notifies specified user via email about error during Spotify import.

    Args:
        musicbrainz_id: the MusicBrainz ID of the user
        error: a description of the error encountered.
    """
    user_email = db_user.get_by_mb_id(musicbrainz_id, fetch_email=True)["email"]
    if not user_email:
        return

    spotify_url = current_app.config['SERVER_ROOT_URL'] + '/profile/music-services/details/'
    text = render_template('emails/spotify_import_error.txt', error=error, link=spotify_url)
    send_mail(
        subject='ListenBrainz Spotify Importer Error',
        text=text,
        recipients=[user_email],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )


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
        # Spotify provides microseconds, but we only give seconds to listenbrainz
        listen = {
            'listened_at': int(parser.parse(play['played_at']).timestamp()),
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
        'listening_from': 'spotify',
        'discnumber': track.get('disc_number'),
        'duration_ms': track.get('duration_ms'),
        'spotify_album_id': album.get('external_urls', {}).get('spotify'),
        # Named 'release_*' because 'release_name' is an official name in the docs
        'release_artist_name': album_artist_name,
        'release_artist_names': release_artist_names,
        # Named 'album_*' because Spotify calls it album and this is spotify-specific
        'spotify_album_artist_ids': spotify_album_artist_ids,
    }
    isrc = track.get('external_ids', {}).get('isrc')
    spotify_url = track.get('external_urls', {}).get('spotify')
    if isrc:
        additional['isrc'] = isrc
    if spotify_url:
        additional['spotify_id'] = spotify_url

    listen['track_metadata'] = {
        'artist_name': artist_name,
        'track_name': track['name'],
        'release_name': album['name'],
        'additional_info': additional,
    }
    return listen


def make_api_request(user: dict, endpoint: str, **kwargs):
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
            break
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
                current_app.logger.warn('Encountered a rate limit, sleeping %d seconds and trying again...', time_to_sleep)
                time.sleep(time_to_sleep)
                delay += 1
                if retries == 0:
                    raise ExternalServiceError('Encountered a rate limit.')

            elif e.http_status in (400, 403):
                current_app.logger.critical('Error from the Spotify API for user %s: %s', user['musicbrainz_id'], str(e), exc_info=True)
                raise ExternalServiceAPIError('Error from the Spotify API while getting listens: %s', str(e))

            elif e.http_status >= 500 and e.http_status < 600:
                # these errors are not our fault, most probably. so just log them and retry.
                current_app.logger.error('Error while trying to get listens for user %s: %s', user['musicbrainz_id'], str(e), exc_info=True)
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
                    raise ExternalServiceAPIError('Could not authenticate with Spotify, please unlink and link your account again.')
            elif e.http_status == 404:
                current_app.logger.error("404 while trying to get listens for user %s", str(user), exc_info=True)
                if retries == 0:
                    raise ExternalServiceError("404 while trying to get listens for user %s" % str(user))
        except Exception as e:
            retries -= 1
            current_app.logger.error('Unexpected error while getting listens: %s', str(e), exc_info=True)
            if retries == 0:
                raise ExternalServiceError('Unexpected error while getting listens: %s' % str(e))

    return recently_played


def get_user_recently_played(user):
    """ Get tracks from the current user’s recently played tracks.
    """
    latest_listened_at_ts = 0
    if user['latest_listened_at']:
        latest_listened_at_ts = int(user['latest_listened_at'].timestamp() * 1000)  # latest listen UNIX ts in ms

    return make_api_request(user, 'current_user_recently_played', limit=50, after=latest_listened_at_ts)


def get_user_currently_playing(user):
    """ Get the user's currently playing track.
    """
    return make_api_request(user, 'current_user_playing_track')


def submit_listens_to_listenbrainz(listenbrainz_user, listens, listen_type=LISTEN_TYPE_IMPORT):
    """ Submit a batch of listens to ListenBrainz

    Args:
        listenbrainz_user (dict): the user whose listens are to be submitted
        listens (list): a list of listens to be submitted
        listen_type: the type of listen (single, import, playing_now)
    """
    username = listenbrainz_user['musicbrainz_id']
    retries = 10
    while retries >= 0:
        try:
            current_app.logger.debug('Submitting %d listens for user %s', len(listens), username)
            insert_payload(listens, listenbrainz_user, listen_type=listen_type)
            current_app.logger.debug('Submitted!')
            break
        except (InternalServerError, ServiceUnavailable) as e:
            retries -= 1
            current_app.logger.error('ISE while trying to import listens for %s: %s', username, str(e))
            if retries == 0:
                raise ExternalServiceError('ISE while trying to import listens: %s', str(e))


def parse_and_validate_spotify_plays(plays, listen_type):
    """ Converts and validates the listens received from the Spotify API.

    Args:
        plays: a list of items received from Spotify
        listen_type: the type of the plays (import or playing now)

    Returns:
        a list of valid listens to submit to ListenBrainz
    """
    listens = []
    for play in plays:
        listen = _convert_spotify_play_to_listen(play, listen_type=listen_type)
        try:
            listens.append(validate_listen(listen, listen_type))
        except APIBadRequest:
            pass
    return listens


def process_one_user(user: dict, service: SpotifyService) -> int:
    """ Get recently played songs for this user and submit them to ListenBrainz.

    Args:
        user (spotify.Spotify): the user whose plays are to be imported.
        service (listenbrainz.domain.spotify.SpotifyService): service to process users

    Raises:
        spotify.SpotifyAPIError: if we encounter errors from the Spotify API.
        spotify.SpotifyListenBrainzError: if we encounter a rate limit, even after retrying.
                                          or if we get errors while submitting the data to ListenBrainz
    Returns:
        the number of recently played listens imported for the user
    """
    try:
        if service.user_oauth_token_has_expired(user):
            user = service.refresh_access_token(user['user_id'], user['refresh_token'])

        listenbrainz_user = db_user.get(user['user_id'])

        listens = []

        # If there is no playback, currently_playing will be None.
        # There are two playing types, track and episode. We use only the
        # track type. Therefore, when the user's playback type is not a track,
        # Spotify will set the item field to null which becomes None after
        # parsing the JSON. Due to these reasons, we cannot simplify the
        # checks below.
        currently_playing = get_user_currently_playing(user)
        if currently_playing is not None:
            currently_playing_item = currently_playing.get('item', None)
            if currently_playing_item is not None:
                current_app.logger.debug('Received a currently playing track for %s', str(user))
                listens = parse_and_validate_spotify_plays([currently_playing_item], LISTEN_TYPE_PLAYING_NOW)
                if listens:
                    submit_listens_to_listenbrainz(listenbrainz_user, listens, listen_type=LISTEN_TYPE_PLAYING_NOW)

        recently_played = get_user_recently_played(user)
        if recently_played is not None and 'items' in recently_played:
            listens = parse_and_validate_spotify_plays(recently_played['items'], LISTEN_TYPE_IMPORT)
            current_app.logger.debug('Received %d tracks for %s', len(listens), str(user))

        # if we don't have any new listens, return
        if len(listens) == 0:
            service.update_user_import_status(user['user_id'])
            return 0

        latest_listened_at = max(listen['listened_at'] for listen in listens)
        submit_listens_to_listenbrainz(listenbrainz_user, listens, listen_type=LISTEN_TYPE_IMPORT)

        # we've succeeded so update the last_updated and latest_listened_at field for this user
        service.update_latest_listen_ts(user['user_id'], latest_listened_at)

        current_app.logger.info('imported %d listens for %s' % (len(listens), str(user['musicbrainz_id'])))
        return len(listens)

    except ExternalServiceInvalidGrantError:
        error_message = "It seems like you've revoked permission for us to read your spotify account"
        service.update_user_import_status(user_id=user['user_id'], error=error_message)
        if not current_app.config['TESTING']:
            notify_error(user['musicbrainz_id'], error_message)
        # user has revoked authorization through spotify ui or deleted their spotify account etc.
        # in any of these cases, we should delete the user's token from.
        service.revoke_user(user['user_id'])
        raise ExternalServiceError("User has revoked spotify authorization")

    except ExternalServiceAPIError as e:
        # if it is an error from the Spotify API, show the error message to the user
        service.update_user_import_status(user_id=user['user_id'], error=str(e))
        if not current_app.config['TESTING']:
            notify_error(user['musicbrainz_id'], str(e))
        raise ExternalServiceError("Could not refresh user token from spotify")


def process_all_spotify_users():
    """ Get a batch of users to be processed and import their Spotify plays.

    Returns:
        (success, failure) where
            success: the number of users whose plays were successfully imported.
            failure: the number of users for whom we faced errors while importing.
    """

    global _listens_imported_since_start, _metric_submission_time

    service = SpotifyService()
    try:
        users = service.get_active_users_to_process()
    except DatabaseException as e:
        current_app.logger.error('Cannot get list of users due to error %s', str(e), exc_info=True)
        return 0, 0

    if not users:
        return 0, 0

    current_app.logger.info('Process %d users...' % len(users))
    success = 0
    failure = 0
    for u in users:
        try:
            _listens_imported_since_start += process_one_user(u, service)
            success += 1
        except ExternalServiceError as e:
            current_app.logger.critical('spotify_reader could not import listens: %s', str(e), exc_info=True)
            failure += 1
        except Exception as e:
            current_app.logger.critical('spotify_reader could not import listens: %s', str(e), exc_info=True)
            failure += 1

    if time.monotonic() > _metric_submission_time:
        _metric_submission_time += METRIC_UPDATE_INTERVAL
        metrics.set("spotify_reader", imported_listens=_listens_imported_since_start)

    current_app.logger.info('Processed %d users successfully!', success)
    current_app.logger.info('Encountered errors while processing %d users.', failure)
    return success, failure


def main():
    app = listenbrainz.webserver.create_app()
    with app.app_context():
        current_app.logger.info('Spotify Reader started...')
        while True:
            t = time.monotonic()
            success, failure = process_all_spotify_users()
            total_users = success + failure
            if total_users > 0:
                total_time = time.monotonic() - t
                avg_time = total_time / total_users
                metrics.set("spotify_reader",
                            users_processed=total_users,
                            time_to_process_all_users=total_time,
                            time_to_process_one_user=avg_time)
                current_app.logger.info('All %d users in batch have been processed.', total_users)
                current_app.logger.info('Total time taken: %.2f s, average time per user: %.2f s.', total_time, avg_time)
            time.sleep(10)


if __name__ == '__main__':
    main()
