#!/usr/bin/env python
from flask import Flask
from flask_socketio import SocketIO, join_room, leave_room
from werkzeug.exceptions import BadRequest
import argparse

from listenbrainz.webserver import load_config
from brainzutils.flask import CustomFlask
from follow_dispatcher import FollowDispatcher

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ListenBrainz Follow Server")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Turn on debugging mode to see stack traces on "
                             "the error pages. This overrides 'DEBUG' value "
                             "in config file.")
    parser.add_argument("-t", "--host", default="0.0.0.0", type=str,
                        help="Which interfaces to listen on. Default: 0.0.0.0.")
    parser.add_argument("-p", "--port", default="8081", type=int,
                        help="Which port to listen on. Default: 8081.")
    args = parser.parse_args()

    fd = FollowDispatcher(app)
    fs.start()

    socketio.run(app, debug=True if args.debug else None,
                    host=args.host, port=args.port)
