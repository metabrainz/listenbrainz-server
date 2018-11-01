#!/usr/bin/python3
import time
import listenbrainz.webserver
import json

from listenbrainz.utils import safely_import_config
safely_import_config()

from dateutil import parser
from flask import current_app
from listenbrainz.domain import spotify
from listenbrainz.webserver.views.api_tools import insert_payload, validate_listen, LISTEN_TYPE_IMPORT
from listenbrainz.db import user as db_user
from listenbrainz.db.exceptions import DatabaseException
from spotipy import SpotifyException
from werkzeug.exceptions import BadRequest, InternalServerError, ServiceUnavailable


def _convert_spotify_play_to_listen(play):
    """ Converts data retrieved from the Spotify API into a listen.

    Args:
        play (dict): a dict that represents a listen retrieved from Spotify

    Returns:
        listen (dict): dict that can be submitted to ListenBrainz
    """
    track = play['track']
    album = track['album']
    # Spotify provides microseconds, but we only give seconds to listenbrainz
    listened_at = int(parser.parse(play['played_at']).timestamp())

    artists = track['artists']
    album_artists = album['artists']
    artist_name = ', '.join([a['name'] for a in artists])
    album_artist_name = ', '.join([a['name'] for a in album_artists])

    additional = {
        'tracknumber': track['track_number'],
        'spotify_artist_ids': [a['external_urls']['spotify'] for a in artists],
        'artist_names': [a['name'] for a in artists],
        'listening_from': 'spotify',
        'discnumber': track['disc_number'],
        'duration_ms': track['duration_ms'],
        'spotify_album_id': track['album']['external_urls']['spotify'],
        # Named 'release_*' because 'release_name' is an official name in the docs
        'release_artist_name': album_artist_name,
        'release_artist_names': [a['name'] for a in album_artists],
        # Named 'album_*' because Spotify calls it album and this is spotify-specific
        'spotify_album_artist_ids': [a['external_urls']['spotify'] for a in album_artists],
    }
    isrc = track.get('external_ids', {}).get('isrc')
    spotify_url = track.get('external_urls', {}).get('spotify')
    if isrc:
        additional['isrc'] = isrc
    if spotify_url:
        additional['spotify_id'] = spotify_url

    track_meta = {
        'artist_name': artist_name,
        'track_name': track['name'],
        'release_name': album['name'],
        'additional_info': additional,
    }

    return {
        'listened_at': listened_at,
        'track_metadata': track_meta,
    }


def get_user_recently_played(user):
    """ Get recently played songs from Spotify for specified user.
    This uses the 'me/player/recently-played' endpoint, which only allows us to get the last 50 plays
    for one user.

    Args:
        user (spotify.Spotify): the user whose plays are to be imported.

    Returns:
        the response from the spotify API consisting of the list of recently played songs.

    Raises:
        spotify.SpotifyAPIError: if we encounter errors from the Spotify API.
        spotify.SpotifyListenBrainzError: if we encounter a rate limit, even after retrying.
    """
    retries = 10
    delay = 1
    tried_to_refresh_token = False

    while retries > 0:
        try:
            recently_played = user.get_spotipy_client()._get("me/player/recently-played", limit=50)
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

            elif e.http_status in (400, 403, 404):
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
                    except SpotifyError as err:
                        raise spotify.SpotifyAPIError('Could not authenticate with Spotify, please unlink and link your account again.')

                    tried_to_refresh_token = True

                else:
                    raise spotify.SpotifyAPIError('Could not authenticate with Spotify, please unlink and link your account again.')
        except Exception as e:
            retries -= 1
            current_app.logger.error('Unexpected error while getting listens: %s', str(e), exc_info=True)
            if retries == 0:
                raise spotify.SpotifyListenBrainzError('Unexpected error while getting listens: %s' % str(e))

    return recently_played


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
    try:
        recently_played = get_user_recently_played(user)
    except (spotify.SpotifyListenBrainzError, spotify.SpotifyAPIError) as e:
        raise

    # convert listens to ListenBrainz format and validate them
    listens = []
    if 'items' in recently_played:
        current_app.logger.debug('Received %d listens from Spotify for %s', len(recently_played['items']),  str(user))
        for item in recently_played['items']:
            listen = _convert_spotify_play_to_listen(item)
            try:
                validate_listen(listen, LISTEN_TYPE_IMPORT)
                listens.append(listen)
            except BadRequest:
                current_app.logger.error('Could not validate listen for user %s: %s', str(user), json.dumps(listen, indent=3), exc_info=True)
                # TODO: api_utils exposes werkzeug exceptions, if it's a more generic module it shouldn't be web-specific

    # if we don't have any new listens, return
    if len(listens) == 0:
        return

    latest_listened_at = max(listen['listened_at'] for listen in listens)
    # try to submit listens to ListenBrainz
    retries = 10
    while retries >= 0:
        try:
            current_app.logger.debug('Submitting %d listens for user %s', len(listens), str(user))
            insert_payload(listens, listenbrainz_user, listen_type=LISTEN_TYPE_IMPORT)
            current_app.logger.debug('Submitted!')
            break
        except (InternalServerError, ServiceUnavailable) as e:
            retries -= 1
            current_app.logger.info('ISE while trying to import listens for %s: %s', str(user), str(e))
            if retries == 0:
                raise spotify.SpotifyListenBrainzError('ISE while trying to import listens: %s', str(e))

    # we've succeeded so update the last_updated field for this user
    spotify.update_latest_listened_at(user.user_id, latest_listened_at)
    spotify.update_last_updated(user.user_id)


def process_all_spotify_users():
    """ Get a batch of users to be processed and import their Spotify plays.

    Returns:
        (success, failure) where
            success: the number of users whose plays were successfully imported.
            failure: the number of users for whom we faced errors while importing.
    """
    current_app.logger.info('Getting list of users to be processed...')
    try:
        users = spotify.get_active_users_to_process()
    except DatabaseException as e:
        current_app.logger.error('Cannot get list of users due to error %s', str(e), exc_info=True)
        return 0, 0

    if not users:
        return 0, 0

    success = 0
    failure = 0
    for u in users:
        t = time.time()
        current_app.logger.info('Importing spotify listens for user %s', str(u))
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
            failure += 1
        except spotify.SpotifyListenBrainzError as e:
            current_app.logger.critical('spotify_reader could not import listens: %s', str(e), exc_info=True)
            failure += 1
        except Exception as e:
            current_app.logger.critical('spotify_reader could not import listens: %s', str(e), exc_info=True)
            failure += 1

        current_app.logger.info('Took a total of %.2f seconds to process user %s', time.time() - t, str(u))

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
