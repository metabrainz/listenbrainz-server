import eventlet
eventlet.monkey_patch()
from flask import Flask, current_app
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit
from werkzeug.exceptions import BadRequest
import argparse
import json

from listenbrainz.webserver import load_config
from brainzutils.flask import CustomFlask
from listenbrainz.follow_server.dispatcher import FollowDispatcher

app = CustomFlask(
    import_name=__name__,
    use_flask_uuid=True,
)
load_config(app)
CORS(app)

# Error handling
from listenbrainz.webserver.errors import init_error_handlers
init_error_handlers(app)

# Logging
app.init_loggers(
    file_config=app.config.get('LOG_FILE'),
    email_config=app.config.get('LOG_EMAIL'),
    sentry_config=app.config.get('LOG_SENTRY')
)
socketio = SocketIO(app)


@socketio.on('json')
def handle_json(data):
    current_app.logger.error('received json: %s' % str(data))
    print('received json: ' + str(data))

    try:
        user = data['user']
    except KeyError:
        raise BadRequest("Missing key 'user'")

    try:
        follow_list = data['follow']
    except KeyError:
        raise BadRequest("Missing key 'follow'")

    if len(follow_list) <= 0:
        raise BadRequest("Follow list must have one or more users.")

    for user in follow_list:
        join_room(user)

@socketio.on('listen')
def emit_new_listen(data):
    current_app.logger.info('got new listen: %s', data)
    emit('listen', data, room='rob') #TODO: fix the room name

@socketio.on('playing_now')
def emit_new_playing_now(data):
    current_app.logger.info('got new playing now: %s', data)
    emit('playing_now', data, room='rob') #TODO: fix the room name


def run_follow_server(host='0.0.0.0', port=8081, debug=True):
    fd = FollowDispatcher(app, socketio)
    fd.start()
    socketio.run(app, debug=debug,
                    host=host, port=port)
