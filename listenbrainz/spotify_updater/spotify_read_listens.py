#!/usr/bin/python3
import time
import listenbrainz.webserver
import json

from listenbrainz.utils import safely_import_config
safely_import_config()

from dateutil import parser
from flask import current_app, render_template
from listenbrainz.domain import spotify
from listenbrainz.webserver.views.api_tools import insert_payload, validate_listen, LISTEN_TYPE_IMPORT, LISTEN_TYPE_PLAYING_NOW
from listenbrainz.db import user as db_user
from listenbrainz.db.exceptions import DatabaseException
from spotipy import SpotifyException
from werkzeug.exceptions import BadRequest, InternalServerError, ServiceUnavailable
from brainzutils.mail import send_mail
from brainzutils import musicbrainz_db
from brainzutils.musicbrainz_db import editor as mb_editor


def notify_error(musicbrainz_row_id, error):
    """ Notifies specified user via email about error during Spotify import.

    Args:
        musicbrainz_row_id (int): the MusicBrainz row ID of the user
        error (str): a description of the error encountered.
    """
    user_email = mb_editor.get_editor_by_id(musicbrainz_row_id)['email']
    spotify_url = current_app.config['SERVER_ROOT_URL'] + '/profile/connect-spotify'
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


def make_api_request(user, endpoint, **kwargs):
    """ Make an request to the Spotify API for particular user at specified endpoint with args.

    Args:
        user (spotify.Spotify): the user whose plays are to be imported.
        endpoint (str): the Spotify API endpoint to which the request is to be made

    Returns:
        the response from the spotify API

    Raises:
        spotify.SpotifyAPIError: if we encounter errors from the Spotify API.
        spotify.SpotifyListenBrainzError: if we encounter a rate limit, even after retrying.
    """
    retries = 10
    delay = 1
    tried_to_refresh_token = False

    while retries > 0:
        try:
            recently_played = user.get_spotipy_client()._get(endpoint, **kwargs)
            break
        except SpotifyException as e:
            retries -= 1
            if e.http_status == 429:
                # Rate Limit Problems -- the client handles these, but it can still give up
                # after a certain number of retries, so we look at the header and try the
                # request again, if the error is raised
                time_to_sleep = e.headers.get('Retry-After', delay)
                current_app.logger.warn('Encountered a rate limit, sleeping %d seconds and trying again...', time_to_sleep)
                time.sleep(time_to_sleep)
                delay += 1
                if retries == 0:
                    raise spotify.SpotifyListenBrainzError('Encountered a rate limit.')

            elif e.http_status in (400, 403):
                current_app.logger.critical('Error from the Spotify API for user %s: %s', str(user), str(e), exc_info=True)
                raise spotify.SpotifyAPIError('Error from the Spotify API while getting listens: %s', str(e))

            elif e.http_status >= 500 and e.http_status < 600:
                # these errors are not our fault, most probably. so just log them and retry.
                current_app.logger.error('Error while trying to get listens for user %s: %s', str(user), str(e), exc_info=True)
                if retries == 0:
                    raise spotify.SpotifyAPIError('Error from the spotify API while getting listens: %s', str(e))

            elif e.http_status == 401:
                # if we get 401 Unauthorized from Spotify, that means our token might have expired.
                # In that case, try to refresh the token, if there is an error even while refreshing
                # give up and report to the user.
                # We only try to refresh the token once, if we still get 401 after that, we give up.
                if not tried_to_refresh_token:
                    try:
                        user = spotify.refresh_user_token(user)
                    except SpotifyException as err:
                        raise spotify.SpotifyAPIError('Could not authenticate with Spotify, please unlink and link your account again.')

                    tried_to_refresh_token = True

                else:
                    raise spotify.SpotifyAPIError('Could not authenticate with Spotify, please unlink and link your account again.')
            elif e.http_status == 404:
                current_app.logger.error("404 while trying to get listens for user %s", str(user), exc_info=True)
                if retries == 0:
                    raise spotify.SpotifyListenBrainzError("404 while trying to get listens for user %s" % str(user))
        except Exception as e:
            retries -= 1
            current_app.logger.error('Unexpected error while getting listens: %s', str(e), exc_info=True)
            if retries == 0:
                raise spotify.SpotifyListenBrainzError('Unexpected error while getting listens: %s' % str(e))

    return recently_played


def get_user_recently_played(user):
    """ Get tracks from the current user’s recently played tracks.
    """
    return make_api_request(user, 'me/player/recently-played', limit=50)


def get_user_currently_playing(user):
    """ Get the user's currently playing track.
    """
    return make_api_request(user, 'me/player/currently-playing')



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
                raise spotify.SpotifyListenBrainzError('ISE while trying to import listens: %s', str(e))


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
            validate_listen(listen, listen_type)
            listens.append(listen)
        except BadRequest as e:
            current_app.logger.error(str(e))
            raise
    return listens


def process_one_user(user):
    """ Get recently played songs for this user and submit them to ListenBrainz.

    Args:
        user (spotify.Spotify): the user whose plays are to be imported.

    Raises:
        spotify.SpotifyAPIError: if we encounter errors from the Spotify API.
        spotify.SpotifyListenBrainzError: if we encounter a rate limit, even after retrying.
                                          or if we get errors while submitting the data to ListenBrainz

    """
    if user.token_expired:
        try:
            user = spotify.refresh_user_token(user)
        except spotify.SpotifyAPIError:
            current_app.logger.error('Could not refresh user token from spotify', exc_info=True)
            raise

    listenbrainz_user = db_user.get(user.user_id)

    currently_playing = get_user_currently_playing(user)
    if currently_playing is not None and 'item' in currently_playing:
        current_app.logger.debug('Received a currently playing track for %s', str(user))
        listens = parse_and_validate_spotify_plays([currently_playing['item']], LISTEN_TYPE_PLAYING_NOW)
        submit_listens_to_listenbrainz(listenbrainz_user, listens, listen_type=LISTEN_TYPE_PLAYING_NOW)


    recently_played = get_user_recently_played(user)
    if recently_played is not None and 'items' in recently_played:
        listens = parse_and_validate_spotify_plays(recently_played['items'], LISTEN_TYPE_IMPORT)
        current_app.logger.debug('Received %d tracks for %s', len(listens), str(user))

    # if we don't have any new listens, return
    if len(listens) == 0:
        return

    latest_listened_at = max(listen['listened_at'] for listen in listens)
    submit_listens_to_listenbrainz(listenbrainz_user, listens, listen_type=LISTEN_TYPE_IMPORT)

    # we've succeeded so update the last_updated field for this user
    spotify.update_latest_listened_at(user.user_id, latest_listened_at)
    spotify.update_last_updated(user.user_id)

    current_app.logger.info('imported %d listens for %s' % (len(listens), str(user)))


def process_all_spotify_users():
    """ Get a batch of users to be processed and import their Spotify plays.

    Returns:
        (success, failure) where
            success: the number of users whose plays were successfully imported.
            failure: the number of users for whom we faced errors while importing.
    """
    try:
        users = spotify.get_active_users_to_process()
    except DatabaseException as e:
        current_app.logger.error('Cannot get list of users due to error %s', str(e), exc_info=True)
        return 0, 0

    if not users:
        return 0, 0

    current_app.logger.info('Process %d users...' % len(users))
    success = 0
    failure = 0
    for u in users:
        t = time.time()
        try:
            process_one_user(u)
            success += 1
        except spotify.SpotifyAPIError as e:
            # if it is an error from the Spotify API, show the error message to the user
            spotify.update_last_updated(
                user_id=u.user_id,
                success=False,
                error_message=str(e),
            )
            if not current_app.config['TESTING']:
                notify_error(u.musicbrainz_row_id, str(e))
            failure += 1
        except spotify.SpotifyListenBrainzError as e:
            current_app.logger.critical('spotify_reader could not import listens: %s', str(e), exc_info=True)
            failure += 1
        except Exception as e:
            current_app.logger.critical('spotify_reader could not import listens: %s', str(e), exc_info=True)
            failure += 1

    current_app.logger.info('Processed %d users successfully!', success)
    current_app.logger.info('Encountered errors while processing %d users.', failure)
    return success, failure


def main():
    app = listenbrainz.webserver.create_app()
    with app.app_context():
        current_app.logger.info('Spotify Reader started...')
        while True:
            t = time.time()
            success, failure = process_all_spotify_users()
            if success + failure > 0:
                current_app.logger.info('All %d users in batch have been processed.', success + failure)
                current_app.logger.info('Total time taken: %.2f s, average time per user: %.2f s.', time.time() - t, (time.time() - t) / (success + failure))
            time.sleep(10)


if __name__ == '__main__':
    main()
