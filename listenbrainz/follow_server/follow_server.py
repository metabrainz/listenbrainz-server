#!/usr/bin/env python
from flask import Flask, current_app
from flask_socketio import SocketIO, join_room, leave_room
from werkzeug.exceptions import BadRequest
import argparse

from listenbrainz.webserver import load_config
from brainzutils.flask import CustomFlask
from listenbrainz.follow_server.dispatcher import FollowDispatcher

app = CustomFlask(
    import_name=__name__,
    use_flask_uuid=True,
)
load_config(app)

# Logging
app.init_loggers(
    file_config=app.config.get('LOG_FILE'),
    email_config=app.config.get('LOG_EMAIL'),
    sentry_config=app.config.get('LOG_SENTRY')
)

socketio = SocketIO(app)

@socketio.on('json')
def handle_json(json):
    current_app.logger.error('received json: %s' % str(json))
    print('received json: ' + str(json))

    try:
        user = json['user']
    except KeyError:
        raise BadRequest("Missing key 'user'")

    try:
        follow_list = json['follow']
    except KeyError:
        raise BadRequest("Missing key 'follow'")

    if len(follow_list) <= 0:
        raise BadRequest("Follow list must have one or more users.")

    for user in follow_list:
        join_room(user)


def run_follow_server(host='0.0.0.0', port=8081, debug=True):

    fd = FollowDispatcher(app)
    fd.start()

    socketio.run(app, debug=debug,
                    host=host, port=port)
