#!/usr/bin/python3
import werkzeug.exceptions
from dateutil import parser
import listenbrainz.webserver
from listenbrainz.domain import spotify
from listenbrainz.webserver.views.api_tools import insert_payload, validate_listen, LISTEN_TYPE_IMPORT
from listenbrainz.db import user as db_user


def _convert_spotify_play_to_listen(play):
    track = play['track']
    album = track['album']
    # Spotify provides microseconds, but we only give seconds to listenbrainz
    listened_at = int(parser.parse(play['played_at']).timestamp())

    artists = track['artists']
    album_artists = album['artists']
    artist_name = ', '.join([a['name'] for a in artists])
    album_artist_name = ', '.join([a['name'] for a in album_artists])

    additional = {'tracknumber': track['track_number'],
                  'spotify_artist_ids': [a['external_urls']['spotify'] for a in artists],
                  'artist_names': [a['name'] for a in artists],
                  'listening_from': 'spotify',
                  'disc_number': track['disc_number'],
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

    track_meta = {'artist_name': artist_name,
                  'track_name': track['name'],
                  'release_name': album['name'],
                  'additional_info': additional
                  }

    return {'listened_at': listened_at,
            'track_metadata': track_meta}


def process_one_user(user):
    if user.token_expired:
        spotify.refresh_user_token(user)
        user = spotify.get_user(user.user_id)

    listenbrainz_user = db_user.get(user.user_id)

    spotipy_client = user.get_spotipy_client()

    recently_played = spotipy_client._get("me/player/recently-played", limit=50)
    # TODO: if error
    # If it's 401, try and refresh one more time and get it
    # If that time fails, report the failure
    # If refresh fails, report the failure
    # What other types of error can we make? (Try bad/invalid keys), 404?
    # If you get status code 429, it means that you have sent too many requests. If this happens, have a look in the Retry-After header
    # spotify.update_error(user.user_id, False, error_msg)
    # https://developer.spotify.com/web-api/user-guide/#response-status-codes
    # 400, can't retry. 401, refresh. 403/404, can't retry.
    # 5xx: retry some times?

    listens = []
    if 'items' in recently_played:
        for item in recently_played['items']:
            listens.append(_convert_spotify_play_to_listen(item))

    try:
        for listen in listens:
            validate_listen(listen, LISTEN_TYPE_IMPORT)
    except werkzeug.exceptions.BadRequest:
        spotify.update_last_updated(user.user_id, False, 'Unable to validate listens')
        return
        # TODO: This is our problem, report it to LB developers with a logger (sentry?)
        # TODO: Skip invalid listens instead of skipping all listens?
        # TODO: api_utils exposes werkzeug exceptions, if it's a more generic module it shouldn't be web-specific

    # TODO: This could fail with some listens, but is something that we create
    # TODO: so we should report to developers and not tell the user?
    insert_payload(listens, listenbrainz_user, listen_type=LISTEN_TYPE_IMPORT)

    spotify.update_last_updated(user.user_id)


def process_all_spotify_users():
    # TODO: logging
    users = spotify.get_active_users_to_process()
    for u in users:
        print("user ")
        print(u)
        process_one_user(u)


def main():
    app = listenbrainz.webserver.create_app()

    with app.app_context():
        process_all_spotify_users()


if __name__ == '__main__':
    main()
