from flask import Flask
from kafka import KafkaClient
import sys
import os

_kafka = None

def create_app():
    app = Flask(__name__)

    # Configuration
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
    import config
    app.config.from_object(config)

    # Logging
    from webserver.loggers import init_loggers
    init_loggers(app)

    # Database connection
    kafka = KafkaClient(app.config['KAFKA_CONNECT'])
    _kafka = kafka

    # Memcached
#    if 'MEMCACHED_SERVERS' in app.config:
#        from db import cache
#        cache.init(app.config['MEMCACHED_SERVERS'],
#                   app.config['MEMCACHED_NAMESPACE'],
#                   debug=1 if app.debug else 0)

    # OAuth
#    from webserver.login import login_manager, provider
#    login_manager.init_app(app)
#    provider.init(app.config['MUSICBRAINZ_CLIENT_ID'],
#                  app.config['MUSICBRAINZ_CLIENT_SECRET'])

    # Error handling
#    from webserver.errors import init_error_handlers
#    init_error_handlers(app)

    # Template utilities
    app.jinja_env.add_extension('jinja2.ext.do')
    from webserver import utils
    app.jinja_env.filters['date'] = utils.reformat_date
    app.jinja_env.filters['datetime'] = utils.reformat_datetime

    # Blueprints
    from webserver.views.index import index_bp
    from webserver.views.listen import listen_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(listen_bp)

    return app
