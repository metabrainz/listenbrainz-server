import logging
import os
import pprint
import sys
from time import sleep

from brainzutils import cache, metrics, sentry
from brainzutils.flask import CustomFlask
from flask import request, url_for, redirect
from flask_login import current_user

from listenbrainz.webserver.utils import get_global_props

API_PREFIX = '/1'

# Check to see if we're running under a docker deployment. If so, don't second guess
# the config file setup and just wait for the correct configuration to be generated.
deploy_env = os.environ.get('DEPLOY_ENV', '')

CONSUL_CONFIG_FILE_RETRY_COUNT = 10
API_LISTENED_AT_ALLOWED_SKEW = 60 * 60 # allow a skew of 1 hour in listened_at submissions


def load_config(app):
    # Load configuration files: If we're running under a docker deployment, wait until
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'config.py')
    if deploy_env:
        print("Checking if consul template generated config file exists: %s" % config_file)
        for i in range(CONSUL_CONFIG_FILE_RETRY_COUNT):
            if not os.path.exists(config_file):
                sleep(1)

        if not os.path.exists(config_file):
            print("No configuration file generated yet. Retried %d times, exiting." % CONSUL_CONFIG_FILE_RETRY_COUNT)
            sys.exit(-1)

        print("loading consul config file %s)" % config_file)

    app.config.from_pyfile(config_file)
    # Output config values and some other info
    if deploy_env in ['prod', 'beta', 'test']:
        print('Configuration values are as follows: ')
        print(pprint.pformat(app.config, indent=4))

        try:
            with open('.git-version') as git_version_file:
                print('Running on git commit: %s' % git_version_file.read().strip())
        except IOError as e:
            print('Unable to retrieve git commit. Error: %s', str(e))


def check_ratelimit_token_whitelist(auth_token):
    """
        Check to see if the given auth_token is a whitelisted auth token.
    """

    from flask import current_app
    return auth_token in current_app.config["WHITELISTED_AUTH_TOKENS"]


def create_app(debug=None):
    """ Generate a Flask app for LB with all configurations done and connections established.

    In the Flask app returned, blueprints are not registered.
    """

    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
    )

    load_config(app)
    if debug is not None:
        app.debug = debug
    # As early as possible, if debug is True, set the log level of our 'listenbrainz' logger to DEBUG
    # to prevent flask from creating a new log handler
    if app.debug:
        logger = logging.getLogger('listenbrainz')
        logger.setLevel(logging.DEBUG)

    # initialize Flask-DebugToolbar if the debug option is True
    if app.debug and app.config['SECRET_KEY']:
        app.init_debug_toolbar()

    sentry_config = app.config.get('LOG_SENTRY')
    if sentry_config:
        sentry.init_sentry(**sentry_config)

    # Initialize BU cache and metrics
    cache.init(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], namespace=app.config['REDIS_NAMESPACE'])
    metrics.init("listenbrainz")

    # Database connections
    from listenbrainz import db
    from listenbrainz.db import timescale as ts
    from listenbrainz import messybrainz as msb
    db.init_db_connection(app.config['SQLALCHEMY_DATABASE_URI'])
    ts.init_db_connection(app.config['SQLALCHEMY_TIMESCALE_URI'])
    msb.init_db_connection(app.config['MESSYBRAINZ_SQLALCHEMY_DATABASE_URI'])

    # Redis connection
    from listenbrainz.webserver.redis_connection import init_redis_connection
    init_redis_connection(app.logger)

    # Timescale connection
    from listenbrainz.webserver.timescale_connection import init_timescale_connection
    init_timescale_connection(app)

    # RabbitMQ connection
    from listenbrainz.webserver.rabbitmq_connection import init_rabbitmq_connection
    try:
        init_rabbitmq_connection(app)
    except ConnectionError:
        app.logger.critical("RabbitMQ service is not up!", exc_info=True)

    if app.config['MB_DATABASE_URI']:
        from brainzutils import musicbrainz_db
        musicbrainz_db.init_db_engine(app.config['MB_DATABASE_URI'])

    # OAuth
    from listenbrainz.webserver.login import login_manager, provider
    login_manager.init_app(app)
    provider.init(app.config['MUSICBRAINZ_CLIENT_ID'],
                  app.config['MUSICBRAINZ_CLIENT_SECRET'])

    # Error handling
    from listenbrainz.webserver.errors import init_error_handlers
    init_error_handlers(app)

    from brainzutils.ratelimit import inject_x_rate_headers, set_user_validation_function
    set_user_validation_function(check_ratelimit_token_whitelist)
    @app.after_request
    def after_request_callbacks(response):
        return inject_x_rate_headers(response)

    # Template utilities
    app.jinja_env.add_extension('jinja2.ext.do')
    from listenbrainz.webserver import utils
    app.jinja_env.filters['date'] = utils.reformat_date
    app.jinja_env.filters['datetime'] = utils.reformat_datetime

    return app


def create_web_app(debug=None):
    """ Generate a Flask app for LB with all configurations done, connections established and endpoints added."""
    app = create_app(debug=debug)

    # Static files
    import listenbrainz.webserver.static_manager
    static_manager.read_manifest()
    app.static_folder = '/static'

    app.context_processor(lambda: dict(
        get_static_path=static_manager.get_static_path,
    ))

    _register_blueprints(app)

    # Admin views
    from listenbrainz import model
    model.db.init_app(app)

    from flask_admin import Admin
    from listenbrainz.webserver.admin.views import HomeView
    admin = Admin(app, index_view=HomeView(name='Home'), template_mode='bootstrap3')
    from listenbrainz.model import ExternalService as ExternalServiceModel
    from listenbrainz.model import User as UserModel
    from listenbrainz.model import ListensImporter as ListensImporterModel
    from listenbrainz.model import ReportedUsers as ReportedUsersModel
    from listenbrainz.model import Playlist as PlaylistModel
    from listenbrainz.model import PlaylistRecording as PlaylistRecordingModel
    from listenbrainz.model.external_service_oauth import ExternalServiceAdminView
    from listenbrainz.model.user import UserAdminView
    from listenbrainz.model.listens_import import ListensImporterAdminView
    from listenbrainz.model.reported_users import ReportedUserAdminView
    from listenbrainz.model.playlist import PlaylistAdminView
    from listenbrainz.model.playlist_recording import PlaylistRecordingAdminView
    admin.add_view(UserAdminView(UserModel, model.db.session, endpoint='user_model'))
    admin.add_view(ExternalServiceAdminView(ExternalServiceModel, model.db.session, endpoint='external_service_model'))
    admin.add_view(ListensImporterAdminView(ListensImporterModel, model.db.session, endpoint='listens_importer_model'))
    admin.add_view(ReportedUserAdminView(ReportedUsersModel, model.db.session, endpoint='reported_users_model'))
    admin.add_view(PlaylistAdminView(PlaylistModel, model.db.session, endpoint='playlist_model'))
    admin.add_view(PlaylistRecordingAdminView(PlaylistRecordingModel, model.db.session, endpoint='playlist_recording_model'))

    @app.before_request
    def before_request_gdpr_check():
        # skip certain pages, static content and the API
        if request.path == url_for('index.gdpr_notice') \
            or request.path == url_for('profile.delete') \
            or request.path == url_for('profile.export_data') \
            or request.path == url_for('login.logout') \
            or request.path.startswith('/static') \
            or request.path.startswith('/1'):
            return
        # otherwise if user is logged in and hasn't agreed to gdpr,
        # redirect them to agree to terms page.
        elif current_user.is_authenticated and current_user.gdpr_agreed is None:
            return redirect(url_for('index.gdpr_notice', next=request.full_path))
    app.logger.info("Flask application created!")
    return app


def create_api_compat_app(debug=None):
    """ Creates application for the AudioScrobbler API.

    The AudioScrobbler API v1.2 requires special views for the root URL so we
    need to create a different app and only register the api_compat blueprints
    """

    app = create_app(debug=debug)

    from listenbrainz.webserver.views.api_compat import api_bp as api_compat_bp
    from listenbrainz.webserver.views.api_compat_deprecated import api_compat_old_bp
    app.register_blueprint(api_compat_bp)
    app.register_blueprint(api_compat_old_bp)

    # add a value into the config dict of the app to note that this is the
    # app for api_compat. This is later used in error handling.
    app.config['IS_API_COMPAT_APP'] = True
    app.logger.info("Flask api compat application created!")
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
    )

    app.config.from_pyfile(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'rtd_config.py'
    ))

    _register_blueprints(app)
    return app


def _register_blueprint_with_context(app, blueprint, **kwargs):
    """Add some global props to a blueprint context and then register it with the app.
    This should only be used for blueprints which render html."""
    @blueprint.context_processor
    def inject_context_processor():
        return {"global_props": get_global_props()}

    app.register_blueprint(blueprint, **kwargs)


def _register_blueprints(app):
    from listenbrainz.webserver.views.index import index_bp
    _register_blueprint_with_context(app, index_bp)

    from listenbrainz.webserver.views.login import login_bp
    _register_blueprint_with_context(app, login_bp, url_prefix='/login')

    from listenbrainz.webserver.views.player import player_bp
    _register_blueprint_with_context(app, player_bp, url_prefix='/player')

    from listenbrainz.webserver.views.playlist import playlist_bp
    _register_blueprint_with_context(app, playlist_bp, url_prefix='/playlist')

    from listenbrainz.webserver.views.profile import profile_bp
    _register_blueprint_with_context(app, profile_bp, url_prefix='/profile')

    from listenbrainz.webserver.views.recommendations_cf_recording import recommendations_cf_recording_bp
    _register_blueprint_with_context(app, recommendations_cf_recording_bp, url_prefix='/recommended/tracks')

    from listenbrainz.webserver.views.user import redirect_bp
    app.register_blueprint(redirect_bp, url_prefix='/my')

    from listenbrainz.webserver.views.user import user_bp
    _register_blueprint_with_context(app, user_bp, url_prefix='/user')

    from listenbrainz.webserver.views.api_compat import api_bp as api_bp_compat
    app.register_blueprint(api_bp_compat)

    from listenbrainz.webserver.views.api import api_bp
    app.register_blueprint(api_bp, url_prefix=API_PREFIX)

    from listenbrainz.webserver.views.feedback_api import feedback_api_bp
    app.register_blueprint(feedback_api_bp, url_prefix=API_PREFIX+'/feedback')

    from listenbrainz.webserver.views.missing_musicbrainz_data_api import missing_musicbrainz_data_api_bp
    app.register_blueprint(missing_musicbrainz_data_api_bp, url_prefix=API_PREFIX+'/missing/musicbrainz')

    from listenbrainz.webserver.views.playlist_api import playlist_api_bp
    app.register_blueprint(playlist_api_bp, url_prefix=API_PREFIX+'/playlist')

    from listenbrainz.webserver.views.recommendations_cf_recording_feedback_api import recommendation_feedback_api_bp
    app.register_blueprint(recommendation_feedback_api_bp, url_prefix=API_PREFIX+'/recommendation/feedback')

    from listenbrainz.webserver.views.recommendations_cf_recording_api import recommendations_cf_recording_api_bp
    app.register_blueprint(recommendations_cf_recording_api_bp, url_prefix=API_PREFIX+'/cf/recommendation')

    from listenbrainz.webserver.views.social_api import social_api_bp
    app.register_blueprint(social_api_bp, url_prefix=API_PREFIX)

    from listenbrainz.webserver.views.stats_api import stats_api_bp
    app.register_blueprint(stats_api_bp, url_prefix=API_PREFIX+'/stats')

    from listenbrainz.webserver.views.status_api import status_api_bp
    app.register_blueprint(status_api_bp, url_prefix=API_PREFIX+'/status')

    from listenbrainz.webserver.views.user_timeline_event_api import user_timeline_event_api_bp
    app.register_blueprint(user_timeline_event_api_bp, url_prefix=API_PREFIX)

    from listenbrainz.webserver.views.pinned_recording_api import pinned_recording_api_bp
    app.register_blueprint(pinned_recording_api_bp, url_prefix=API_PREFIX)

    from listenbrainz.webserver.views.color_api import color_api_bp
    app.register_blueprint(color_api_bp, url_prefix=API_PREFIX+'/color')

    from listenbrainz.webserver.views.metadata_api import metadata_bp
    app.register_blueprint(metadata_bp, url_prefix=API_PREFIX+'/metadata')
