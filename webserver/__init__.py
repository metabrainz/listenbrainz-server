from flask import Flask, g
from messybrainz import db
import sys
import os
import logging

def create_app():
    app = Flask(__name__)

    # Configuration
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
    import config
    app.config.from_object(config)

    # Redis (cache)
    from brainzutils import cache
    if "REDIS_HOST" in app.config and \
       "REDIS_PORT" in app.config and \
       "REDIS_NAMESPACE" in app.config:
        cache.init(
            host=app.config["REDIS_HOST"],
            port=app.config["REDIS_PORT"],
            namespace=app.config["REDIS_NAMESPACE"],
        )
    else:
        logging.warning("Redis is not defined in config file. Skipping initialization.")

    # Logging
    from webserver.loggers import init_loggers
    init_loggers(app)

    # Extensions
    from flask_uuid import FlaskUUID
    FlaskUUID(app)

    # Error handling
    from webserver.errors import init_error_handlers
    init_error_handlers(app)

    # Template utilities
    app.jinja_env.add_extension('jinja2.ext.do')
    from webserver import utils
    app.jinja_env.filters['date'] = utils.reformat_date
    app.jinja_env.filters['datetime'] = utils.reformat_datetime

    # Blueprints
    from webserver.views.index import index_bp
    from webserver.views.api import api_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(api_bp)

    @app.before_request
    def before_request():
        db.init_db_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    @app.teardown_request
    def teardown_request(exception):
        pass

    return app
