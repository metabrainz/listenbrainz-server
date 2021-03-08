import eventlet

from flask import request
from flask_socketio import SocketIO, join_room, emit, rooms, leave_room
from werkzeug.exceptions import BadRequest
from brainzutils.flask import CustomFlask

from listenbrainz.webserver import load_config
from listenbrainz.webserver.errors import init_error_handlers
from listenbrainz.websockets.listens_dispatcher import ListensDispatcher

eventlet.monkey_patch()

app = CustomFlask(import_name=__name__, use_flask_uuid=True)
load_config(app)
init_error_handlers(app)
app.init_loggers(
    file_config=app.config.get('LOG_FILE'),
    email_config=app.config.get('LOG_EMAIL'),
    sentry_config=app.config.get('LOG_SENTRY')
)

socketio = SocketIO(app, cors_allowed_origins='*')


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
    emit('playlist_changed', data, room=playlist_id)


@socketio.on('joined')
def joined(data):
    if 'playlist_id' not in data:
        raise BadRequest("Missing key 'playlist_id'")

    room = data['playlist_id']
    join_room(room)
    emit('joined', {'status': 'success'}, room=room)


def run_websockets(host='0.0.0.0', port=8082, debug=True):
    dispatcher = ListensDispatcher(app, socketio)
    dispatcher.start()
    socketio.run(app, debug=debug, host=host, port=port)
