import eventlet
from threading import Thread

from brainzutils import sentry
from flask_login import current_user
from flask_socketio import SocketIO, join_room, emit, disconnect
from werkzeug.exceptions import BadRequest

from listenbrainz.webserver import create_app
from listenbrainz.db import playlist as db_playlist
from listenbrainz.websockets.listens_dispatcher import ListensDispatcher

eventlet.monkey_patch()

app = create_app()
sentry_config = app.config.get('LOG_SENTRY')
if sentry_config:
    sentry.init_sentry(**sentry_config)

socketio = SocketIO(app, cors_allowed_origins='*', logger=True, engineio_logger=True)


@socketio.on('json')
def handle_json(data):
    try:
        user = data['user']
    except KeyError:
        raise BadRequest("Missing key 'user'")
    join_room(user)


@socketio.on('change_playlist')
def dispatch_playlist_updates(data):
    identifier = data['identifier']
    idx = identifier.rfind('/')
    playlist_id = identifier[idx + 1:]
    emit('playlist_changed', data, to=playlist_id)


@socketio.on('joined')
def joined(data):
    if 'playlist_id' not in data:
        raise BadRequest("Missing key 'playlist_id'")
    playlist_mbid = data['playlist_id']
    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if current_user.is_authenticated and playlist.is_modifiable_by(current_user.id):
        join_room(playlist_mbid)
        emit('joined', {'status': 'success'}, to=playlist_mbid)
    else:
        disconnect()


def run_websockets(host='0.0.0.0', port=7082, debug=True):
    dispatcher = ListensDispatcher(app, socketio)
    Thread(target=dispatcher.start).start()
    socketio.run(app, debug=debug, host=host, port=port)
