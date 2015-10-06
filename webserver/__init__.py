from flask import Flask, current_app
import sys
import os


def create_cassandra():
    from cassandra_connection import init_cassandra_connection
    return init_cassandra_connection(current_app.config['CASSANDRA_SERVER'], current_app.config['CASSANDRA_KEYSPACE'])


def create_app():
    app = Flask(__name__)

    # Read the Docs builder doesn't have any of our databases or special
    # packages (like MessyBrainz), so we have to ignore these initialization
    # steps. Only blueprints/views are needed to render documentation.
    on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
    if not on_rtd:

        # Configuration
        sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
        sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../listenstore"))
        import config
        app.config.from_object(config)

        # Logging
        from webserver.loggers import init_loggers
        init_loggers(app)

        # Kafka connection
        from kafka_connection import init_kafka_connection
        init_kafka_connection(app.config['KAFKA_CONNECT'])

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

        # Template utilities
        app.jinja_env.add_extension('jinja2.ext.do')
        from webserver import utils
        app.jinja_env.filters['date'] = utils.reformat_date
        app.jinja_env.filters['datetime'] = utils.reformat_datetime

    # Blueprints
    from webserver.views.index import index_bp
    from webserver.views.login import login_bp
    from webserver.views.api import api_bp
    from webserver.views.user import user_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp, url_prefix='/login')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(api_bp)

    return app
