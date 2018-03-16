import os
import pprint
import sys
from time import sleep
from shutil import copyfile

from brainzutils.flask import CustomFlask

API_PREFIX = '/1'

# Check to see if we're running under a docker deployment. If so, don't second guess
# the config file setup and just wait for the correct configuration to be generated.
deploy_env = os.environ.get('DEPLOY_ENV', '')

CONSUL_CONFIG_FILE_RETRY_COUNT = 10
API_LISTENED_AT_ALLOWED_SKEW = 60 * 60 # allow a skew of 1 hour in listened_at submissions

def create_influx(app):
    from listenbrainz.webserver.influx_connection import init_influx_connection
    return init_influx_connection(app.logger, {
        'INFLUX_HOST': app.config['INFLUX_HOST'],
        'INFLUX_PORT': app.config['INFLUX_PORT'],
        'INFLUX_DB_NAME': app.config['INFLUX_DB_NAME'],
        'REDIS_HOST': app.config['REDIS_HOST'],
        'REDIS_PORT': app.config['REDIS_PORT'],
        'REDIS_NAMESPACE': app.config['REDIS_NAMESPACE'],
    })


def create_redis(app):
    from listenbrainz.webserver.redis_connection import init_redis_connection
    init_redis_connection(app.logger, app.config['REDIS_HOST'], app.config['REDIS_PORT'])


def create_rabbitmq(app):
    from listenbrainz.webserver.rabbitmq_connection import init_rabbitmq_connection
    init_rabbitmq_connection(app)


def gen_app(config_path=None, debug=None):
    """ Generate a Flask app for LB with all configurations done and connections established.

    In the Flask app returned, blueprints are not registered.
    """
    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
    )

    print("Starting metabrainz service with %s environment." % deploy_env);

    # Configuration
    print("loading %s" % os.path.join( os.path.dirname(os.path.realpath(__file__)), '..', 'default_config.py'))
    app.config.from_pyfile(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'default_config.py'
    ))

    # Load configuration files: If we're running under a docker deployment, wait until
    # the consul configuration has been copied to custom_config.py
    custom_config = os.path.join( os.path.dirname(os.path.realpath(__file__)), '..', 'custom_config.py' )
    if deploy_env:
        print("Checking if consul template generated config file exists: %s" % custom_config)
        for i in range(CONSUL_CONFIG_FILE_RETRY_COUNT):
            if not os.path.exists(custom_config):
                sleep(1)

        if not os.path.exists(custom_config):
            print("No configuration file generated yet. Retried %d times, exiting." % CONSUL_CONFIG_FILE_RETRY_COUNT);
            sys.exit(-1)

        print("loading consul config file %s)" % os.path.join( os.path.dirname(os.path.realpath(__file__)), '..', 'custom_config.py'))
        app.config.from_pyfile(custom_config)

    else:
        print("loading custom config %s" % custom_config)
        app.config.from_pyfile(custom_config, silent=True)

    if config_path:
        print("loading additional config %s" % config_path)
        app.config.from_pyfile(config_path)


    if debug is not None:
        app.debug = debug

    # initialize Flask-DebugToolbar if the debug option is True
    if app.debug and app.config['SECRET_KEY']:
        app.init_debug_toolbar()

    # Output config values and some other info
    print('Configuration values are as follows: ')
    print(pprint.pformat(app.config, indent=4))
    try:
        with open('.git-version') as git_version_file:
            print('Running on git commit: %s', git_version_file.read().strip())
    except IOError as e:
        print('Unable to retrieve git commit. Error: %s', str(e))

    # Logging
    app.init_loggers(
        file_config=app.config.get('LOG_FILE'),
        email_config=app.config.get('LOG_EMAIL'),
        sentry_config=app.config.get('LOG_SENTRY')
    )

    # Redis connection
    create_redis(app)

    # Influx connection
    create_influx(app)

    # RabbitMQ connection
    create_rabbitmq(app)

    # Database connection
    from listenbrainz import db
    db.init_db_connection(app.config['SQLALCHEMY_DATABASE_URI'])
    from listenbrainz.webserver.external import messybrainz
    messybrainz.init_db_connection(app.config['MESSYBRAINZ_SQLALCHEMY_DATABASE_URI'])

    # OAuth
    from listenbrainz.webserver.login import login_manager, provider
    login_manager.init_app(app)
    provider.init(app.config['MUSICBRAINZ_CLIENT_ID'],
                  app.config['MUSICBRAINZ_CLIENT_SECRET'])

    # Error handling
    from listenbrainz.webserver.errors import init_error_handlers
    init_error_handlers(app)

    from listenbrainz.webserver import rate_limiter
    @app.after_request
    def after_request_callbacks(response):
        return rate_limiter.inject_x_rate_headers(response)

    # Template utilities
    app.jinja_env.add_extension('jinja2.ext.do')
    from listenbrainz.webserver import utils
    app.jinja_env.filters['date'] = utils.reformat_date
    app.jinja_env.filters['datetime'] = utils.reformat_datetime

    return app


def create_app(config_path=None, debug=None):

    app = gen_app(config_path=config_path, debug=debug)
    _register_blueprints(app)
    return app


def create_api_compat_app(config_path=None, debug=None):
    """ Creates application for the AudioScrobbler API.

    The AudioScrobbler API v1.2 requires special views for the root URL so we
    need to create a different app and only register the api_compat blueprints
    """

    app = gen_app(config_path=config_path, debug=debug)

    from listenbrainz.webserver.views.api_compat import api_bp as api_compat_bp
    from listenbrainz.webserver.views.api_compat_deprecated import api_compat_old_bp
    app.register_blueprint(api_compat_bp)
    app.register_blueprint(api_compat_old_bp)

    # add a value into the config dict of the app to note that this is the
    # app for api_compat. This is later used in error handling.
    app.config['IS_API_COMPAT_APP'] = True

    return app


def create_app_rtfd():
    """Creates application for generating the documentation.

    Read the Docs builder doesn't have any of our databases or special
    packages (like MessyBrainz), so we have to ignore these initialization
    steps. Only blueprints/views are needed to render documentation.
    """
    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
        use_debug_toolbar=False,
    )

    app.config.from_pyfile(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'default_config.py'
    ))

    _register_blueprints(app)
    return app


def _register_blueprints(app):
    from listenbrainz.webserver.views.index import index_bp
    from listenbrainz.webserver.views.login import login_bp
    from listenbrainz.webserver.views.api import api_bp
    from listenbrainz.webserver.views.api_compat import api_bp as api_bp_compat
    from listenbrainz.webserver.views.user import user_bp
    from listenbrainz.webserver.views.profile import profile_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp, url_prefix='/login')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(api_bp, url_prefix=API_PREFIX)
    app.register_blueprint(api_bp_compat)
