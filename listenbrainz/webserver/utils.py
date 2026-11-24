import string
import random

import orjson
from flask import current_app, g, request
from flask_login import current_user

from listenbrainz.webserver import db_conn, meb_conn
from listenbrainz.webserver.views.views_utils import get_current_spotify_user, get_current_youtube_user, \
    get_current_critiquebrainz_user, get_current_musicbrainz_user, get_current_soundcloud_user, get_current_apple_music_user, \
    get_current_funkwhale_user, get_current_navidrome_user
import listenbrainz.db.donation as db_donation
from listenbrainz.db.global_props import get_global_props_data

METABRAINZ_PROFILE_URL = "https://metabrainz.org/profile"
EMAIL_REQUIRED_BLOG_URL = "https://blog.metabrainz.org/?p=8915"

EMAIL_VERIFICATION_REQUIRED_MESSAGE = \
    'Please check your inbox for a verification email, or go to your MetaBrainz profile page ' \
    'to verify your email: ' \
    f'{METABRAINZ_PROFILE_URL}. ' \
    f'Read the blog post at {EMAIL_REQUIRED_BLOG_URL} to understand why we need your email.'

REJECT_LISTENS_WITHOUT_EMAIL_ERROR = \
    'The listens were rejected because your MetaBrainz account does not have a verified email address. ' \
    f'{EMAIL_VERIFICATION_REQUIRED_MESSAGE}'

CONNECT_SERVICES_WITHOUT_EMAIL_ERROR = \
    'You need to verify an email address before connecting a service. ' \
    f'{EMAIL_VERIFICATION_REQUIRED_MESSAGE}'

REJECT_LISTENS_FROM_PAUSED_USER_ERROR = \
    'User account is paused and is currently not accepting listens. ' \
    'Feel free to contact us if you have any questions about this. ' \
    'https://metabrainz.org/contact'


def generate_string(length):
    """Generates random string with a specified length."""
    return ''.join([random.SystemRandom().choice(
        string.ascii_letters + string.digits
    ) for _ in range(length)])


def sizeof_readable(num, suffix='B'):
    """ Converts the size in human readable format """

    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yb', suffix)


def number_readable(num: int):
    # Solution by rtaft from https://stackoverflow.com/a/45846841/4904467
    """ Converts a number to a short human-readable format (1.2K, 6.6M, etc.)"""
    suffixes = ['', 'K', 'M', 'B', 'T']
    num = float('{:.2g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), suffixes[magnitude])


def reformat_date(value, fmt="%b %d, %Y"):
    return value.strftime(fmt)


def reformat_datetime(value, fmt="%b %d, %Y, %H:%M %Z"):
    return value.strftime(fmt)


def get_current_user_page_data():
    """ The logged-in user's data for an HTML page, fetched once per request, or None if nobody is logged in.

    get_global_props and get_initial_alerts both run on every rendered page and share this.
    """
    if not current_user.is_authenticated:
        return None
    if "global_props_data" not in g:
        g.global_props_data = get_global_props_data(db_conn, current_user.id)
    return g.global_props_data


def get_global_props():
    """Generate React props that should be available on all html pages.
    These are passed into the template context on website blueprints as
    an encoded json string.
    The props include:
     - information about the current logged in user
     - auth details for spotify, youtube and other music services the current user is connected to
     - sentry dsn
     - API url for frontend to connect to.
     - user preferences
    """
    current_user_data = {}
    data = get_current_user_page_data()
    if current_user.is_authenticated:
        current_user_data = {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
            "auth_token": current_user.auth_token,
        }

    sentry_config = current_app.config.get("LOG_SENTRY", {})

    props = {
        "api_url": current_app.config["API_URL"],
        "websockets_url": current_app.config["WEBSOCKETS_SERVER_URL"],
        "sentry_dsn": sentry_config.get("dsn"),
        "current_user": current_user_data,
        "spotify": get_current_spotify_user(data),
        "youtube": get_current_youtube_user(),
        "critiquebrainz": get_current_critiquebrainz_user(data),
        "musicbrainz": get_current_musicbrainz_user(data),
        "soundcloud": get_current_soundcloud_user(data),
        "appleMusic": get_current_apple_music_user(data),
        "funkwhale": get_current_funkwhale_user(data),
        "navidrome": get_current_navidrome_user(data),
        "sentry_traces_sample_rate": sentry_config.get("traces_sample_rate", 0.0),
    }

    if current_user.is_authenticated:
        user_setting = data["user_setting"]
        if user_setting is not None:
            props["user_preferences"] = {"brainzplayer": user_setting["brainzplayer"]}
            if user_setting["flair"] is not None:
                props["flair"] = user_setting["flair"]

        # the flair is cosmetic, the page must not fail because the MetaBrainz database is unavailable
        try:
            show_flair = db_donation.is_user_eligible_donor(meb_conn, current_user.musicbrainz_row_id)
        except Exception:
            current_app.logger.error("Could not check donor flair for user %s", current_user.id, exc_info=True)
            show_flair = None
        if show_flair is not None:
            props["show_flair"] = show_flair

    return orjson.dumps(props).decode("utf-8")


def get_initial_alerts():
    """Generate initial alerts for the React frontend."""
    alerts = []

    from listenbrainz.webserver import redis_connection
    try:
        messages = redis_connection._redis.get_admin_flash_messages()
    except Exception:
        current_app.logger.error("Could not load admin flash messages from Redis", exc_info=True)
        messages = []

    for message in messages:
        alerts.append({
            "id": message["id"],
            "level": message["level"],
            "message": message["message"],
        })

    data = get_current_user_page_data()
    if data is not None:
        error = data["spotify_import_error"]
        if error and error.get("reason") == "invalid_grant":
            alerts.append({
                "id": "spotify-reconnect-required",
                "level": "error",
                "message": (
                    'Your Spotify connection has expired or been revoked, so imports have stopped. '
                    '<a href="/settings/music-services/details/">Reconnect Spotify</a> to resume imports.'
                ),
            })

    return orjson.dumps(alerts).decode("utf-8")


def parse_boolean_arg(name, default=None):
    from listenbrainz.webserver.errors import APIBadRequest
    value = request.args.get(name)
    if not value:
        return default

    value = value.lower()
    if value not in ["true", "false"]:
        raise APIBadRequest("Invalid %s argument: %s. Must be 'true' or 'false'" % (name, value))

    return True if value == "true" else False
