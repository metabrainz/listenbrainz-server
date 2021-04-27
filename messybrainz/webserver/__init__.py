import logging
import os
import sys

from brainzutils.flask import CustomFlask
from messybrainz import db


def create_app(debug=None, config_path=None):
    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
    )

    # Configuration
    app.config.from_pyfile(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'default_config.py'
    ))
    app.config.from_pyfile(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'custom_config.py'
    ), silent=True)

    if config_path:
        app.config.from_pyfile(config_path)

    if debug is not None:
        app.debug = debug

    if app.debug and app.config['SECRET_KEY']:
        app.init_debug_toolbar()

    # Redis (cache)
    from brainzutils import cache
    try:
        cache.init(
            host=app.config["REDIS_HOST"],
            port=app.config["REDIS_PORT"],
            namespace=app.config["REDIS_NAMESPACE"],
        )
    except KeyError as e:
        logging.error("Redis is not defined in config file. Error: {}".format(e))
        raise

    # Logging
    app.init_loggers(
        file_config=app.config.get('LOG_FILE'),
        email_config=app.config.get('LOG_EMAIL'),
        sentry_config=app.config.get('LOG_SENTRY')
    )

    # Extensions
    from flask_uuid import FlaskUUID
    FlaskUUID(app)

    # Error handling
    from messybrainz.webserver.errors import init_error_handlers
    init_error_handlers(app)

    # Template utilities
    app.jinja_env.add_extension('jinja2.ext.do')
    from messybrainz.webserver import utils
    app.jinja_env.filters['date'] = utils.reformat_date
    app.jinja_env.filters['datetime'] = utils.reformat_datetime

    # Blueprints
    from messybrainz.webserver.views.index import index_bp
    from messybrainz.webserver.views.api import api_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(api_bp)

    db.init_db_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    return app

application = create_app()
