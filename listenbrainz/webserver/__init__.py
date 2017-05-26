from __future__ import absolute_import
from flask import Flask, current_app
import sys
import os
from listenbrainz.webserver.scheduler import ScheduledJobs

def create_influx(app):
    from listenbrainz.webserver.influx_connection import init_influx_connection
    return init_influx_connection(app.logger, {
        'INFLUX_HOST': app.config['INFLUX_HOST'],
        'INFLUX_PORT': app.config['INFLUX_PORT'],
        'INFLUX_DB_NAME': app.config['INFLUX_DB_NAME'],
        'REDIS_HOST': app.config['REDIS_HOST'],
        'REDIS_PORT': app.config['REDIS_PORT'],
    })

def create_redis(app):
    from listenbrainz.webserver.redis_connection import init_redis_connection
    init_redis_connection(app.logger, app.config['REDIS_HOST'], app.config['REDIS_PORT'])

def create_rabbitmq(app):
    from listenbrainz.webserver.rabbitmq_connection import init_rabbitmq_connection
    init_rabbitmq_connection(app)

def schedule_jobs(app):
    """ Init all the scheduled jobs """
    app.scheduledJobs = ScheduledJobs(app.config)


def create_app():
    app = Flask(__name__)

    # Configuration
    from listenbrainz import config
    app.config.from_object(config)

    # Logging
    from listenbrainz.webserver.loggers import init_loggers
    init_loggers(app)

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
    from listenbrainz.webserver.views.index import index_bp
    from listenbrainz.webserver.views.login import login_bp
    from listenbrainz.webserver.views.api import api_bp
    from listenbrainz.webserver.views.api_compat import api_bp as api_bp_compat
    from listenbrainz.webserver.views.user import user_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp, url_prefix='/login')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(api_bp)
    app.register_blueprint(api_bp_compat)
