import logging
import os
import pprint
import sys
from time import sleep

from brainzutils import cache, metrics, sentry
from brainzutils.flask import CustomFlask
from flask import request, url_for, redirect, g, jsonify, current_app
from flask_login import current_user
from werkzeug.local import LocalProxy
from flask_htmx import HTMX

from listenbrainz import db
from listenbrainz.db import (
    create_test_database_connect_strings,
    timescale,
    donation
)
from listenbrainz.db.timescale import create_test_timescale_connect_strings
from listenbrainz.webserver.converters import NotApiPathConverter, UsernameConverter

API_PREFIX = '/1'
CONSUL_CONFIG_FILE_RETRY_COUNT = 10
API_LISTENED_AT_ALLOWED_SKEW = 3600  # 1 hour
RATELIMIT_PER_TOKEN = 100_000
DEPLOY_ENV = os.getenv('DEPLOY_ENV', '')


def _get_conn(conn_name, engine):
    """Return a cached DB connection for the current request context."""
    conn = getattr(g, conn_name, None)
    if conn is None and engine is not None:
        conn = g.__setattr__(conn_name, engine.connect()) or getattr(g, conn_name)
    return conn


db_conn = LocalProxy(lambda: _get_conn("_db_conn", db.engine))
ts_conn = LocalProxy(lambda: _get_conn("_ts_conn", timescale.engine))
meb_conn = LocalProxy(lambda: _get_conn("_meb_conn", donation.engine))


def load_config(app):
    """Load configuration, retrying for Docker deployments if needed."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')

    if DEPLOY_ENV:
        for attempt in range(CONSUL_CONFIG_FILE_RETRY_COUNT):
            if os.path.exists(config_path):
                break
            sleep(1)
        else:
            print(f"Config not found after {CONSUL_CONFIG_FILE_RETRY_COUNT} retries. Exiting.")
            sys.exit(1)

        print(f"Loading consul config file: {config_path}")

    app.config.from_pyfile(config_path)

    if DEPLOY_ENV in {'prod', 'beta', 'test'}:
        print("Loaded configuration:")
        print(pprint.pformat(app.config, indent=4))
        try:
            with open('.git-version') as f:
                print(f"Running on git commit: {f.read().strip()}")
        except IOError as e:
            print(f"Unable to retrieve git commit: {e}")


def check_ratelimit_token_whitelist(auth_token):
    """Return True if auth_token is whitelisted."""
    return auth_token in current_app.config.get("WHITELISTED_AUTH_TOKENS", [])


def _close_connections():
    """Close all database connections cleanly."""
    for attr in ("_db_conn", "_ts_conn", "_meb_conn"):
        conn = getattr(g, attr, None)
        if conn:
            conn.close()
            delattr(g, attr)


def create_app(debug=None):
    """Create and configure the base Flask app."""
    app = CustomFlask(__name__)
    load_config(app)

    if debug is not None:
        app.debug = debug

    if app.debug:
        logging.getLogger('listenbrainz').setLevel(logging.DEBUG)
        if app.config.get('SECRET_KEY'):
            app.init_debug_toolbar()

    app.url_map.converters.update({
        "not_api_path": NotApiPathConverter,
        "mb_username": UsernameConverter
    })

    # Sentry and Metrics setup
    if sentry_config := app.config.get('LOG_SENTRY'):
        sentry.init_sentry(**sentry_config)

    cache.init(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        namespace=app.config['REDIS_NAMESPACE']
    )
    metrics.init("listenbrainz")

    # Database setup
    if "PYTHON_TESTS_RUNNING" in os.environ:
        db.init_db_connection(create_test_database_connect_strings()["DB_CONNECT"])
        timescale.init_db_connection(create_test_timescale_connect_strings()["DB_CONNECT"])
    else:
        db.init_db_connection(app.config["SQLALCHEMY_DATABASE_URI"])
        timescale.init_db_connection(app.config["SQLALCHEMY_TIMESCALE_URI"])
        if uri := app.config.get("SQLALCHEMY_METABRAINZ_URI"):
            donation.init_meb_db_connection(uri)

    app.teardown_request(lambda exc: _close_connections())

    # Other connections
    from listenbrainz.webserver.redis_connection import init_redis_connection
    from listenbrainz.webserver.timescale_connection import init_timescale_connection
    from listenbrainz.db import couchdb
    from listenbrainz.webserver.rabbitmq_connection import init_rabbitmq_connection

    init_redis_connection(app.logger)
    init_timescale_connection(app)

    couchdb.init(
        app.config['COUCHDB_USER'],
        app.config['COUCHDB_ADMIN_KEY'],
        app.config['COUCHDB_HOST'],
        app.config['COUCHDB_PORT'],
    )

    try:
        init_rabbitmq_connection(app)
    except ConnectionError:
        app.logger.critical("RabbitMQ service is not up!", exc_info=True)

    if mb_uri := app.config.get('MB_DATABASE_URI'):
        from brainzutils import musicbrainz_db
        musicbrainz_db.init_db_engine(mb_uri)

    # Auth, error handling, and rate limiting
    from listenbrainz.webserver.login import login_manager
    from listenbrainz.webserver.errors import init_error_handlers
    from brainzutils.ratelimit import (
        inject_x_rate_headers, set_user_validation_function,
        set_rate_limits, ratelimit_per_ip_default, ratelimit_window_default
    )

    login_manager.init_app(app)
    init_error_handlers(app)

    set_user_validation_function(check_ratelimit_token_whitelist)
    set_rate_limits(RATELIMIT_PER_TOKEN, ratelimit_per_ip_default, ratelimit_window_default)

    @app.after_request
    def apply_response_headers(response):
        response.cache_control.private = True
        response.cache_control.public = False
        return inject_x_rate_headers(response)

    # Jinja utilities
    from listenbrainz.webserver import utils
    app.jinja_env.add_extension('jinja2.ext.do')
    app.jinja_env.filters.update({
        'date': utils.reformat_date,
        'datetime': utils.reformat_datetime
    })

    return app
