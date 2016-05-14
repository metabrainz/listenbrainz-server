from flask import Flask, current_app
import sys
import os
import messybrainz
import messybrainz.db

from .scheduler import ScheduledJobs

def create_cassandra():
    from cassandra_connection import init_cassandra_connection
    return init_cassandra_connection(current_app.config['CASSANDRA_SERVER'], current_app.config['CASSANDRA_KEYSPACE'],
        current_app.config['CASSANDRA_REPLICATION_FACTOR'])

def create_postgres():
    from postgres_connection import init_postgres_connection
    return init_postgres_connection(current_app.config['SQLALCHEMY_DATABASE_URI'])


def create_app():
    app = Flask(__name__)

    # Configuration
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../listenstore"))
    import config
    app.config.from_object(config)

    # Run the scheduled jobs
    scheduledJobs = ScheduledJobs(app.config)

    # Logging
    from webserver.loggers import init_loggers
    init_loggers(app)

    # Kafka connection
    from kafka_connection import init_kafka_connection
    init_kafka_connection(app.config['KAFKA_CONNECT'])

    # Redis connection
    from redis_connection import init_redis_connection
    init_redis_connection()

    # Database connection
    import db
    db.init_db_connection(app)
    from webserver.external import messybrainz
    messybrainz.init_db_connection(app.config['MESSYBRAINZ_SQLALCHEMY_DATABASE_URI'])

    # OAuth
    from webserver.login import login_manager, provider
    login_manager.init_app(app)
    provider.init(app.config['MUSICBRAINZ_CLIENT_ID'],
                  app.config['MUSICBRAINZ_CLIENT_SECRET'])

    # Error handling
    from webserver.errors import init_error_handlers
    init_error_handlers(app)

    from webserver import rate_limiter
    @app.after_request
    def after_request_callbacks(response):
        return rate_limiter.inject_x_rate_headers(response)

    # Template utilities
    app.jinja_env.add_extension('jinja2.ext.do')
    from webserver import utils
    app.jinja_env.filters['date'] = utils.reformat_date
    app.jinja_env.filters['datetime'] = utils.reformat_datetime

    _register_blueprints(app)

    return app


def create_app_rtfd():
    """Creates application for generating the documentation.

    Read the Docs builder doesn't have any of our databases or special
    packages (like MessyBrainz), so we have to ignore these initialization
    steps. Only blueprints/views are needed to render documentation.
    """
    app = Flask(__name__)
    _register_blueprints(app)
    return app


def _register_blueprints(app):
    from webserver.views.index import index_bp
    from webserver.views.login import login_bp
    from webserver.views.api import api_bp
    from webserver.views.user import user_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp, url_prefix='/login')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(api_bp)
