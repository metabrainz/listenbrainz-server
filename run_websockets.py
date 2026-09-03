# gevent monkey-patching must happen before all other imports to ensure
# cooperative I/O in every library (kombu, amqp, etc.). hence, this command
# is in a separate script.
import gevent.monkey
gevent.monkey.patch_all()

import click

from listenbrainz import webserver


@click.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=7082, show_default=True)
@click.option("--debug", "-d", is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides 'DEBUG' value in the config file.")
def main(host, port, debug=True):
    from listenbrainz.websockets.websockets import run_websockets
    application = webserver.create_app()
    with application.app_context():
        run_websockets(application, host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
