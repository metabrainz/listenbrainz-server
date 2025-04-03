import string
import random

import orjson
from flask import current_app, request
from flask_login import current_user

from listenbrainz.webserver import db_conn, meb_conn
from listenbrainz.webserver.views.views_utils import get_current_spotify_user, get_current_youtube_user, \
    get_current_critiquebrainz_user, get_current_musicbrainz_user, get_current_soundcloud_user, get_current_apple_music_user
import listenbrainz.db.user_setting as db_usersetting
import listenbrainz.db.donation as db_donation

REJECT_LISTENS_WITHOUT_EMAIL_ERROR = \
    'The listens were rejected because the user does not has not provided an email. ' \
    'Please visit https://musicbrainz.org/account/edit to add an email address. ' \
    'Read the blog post at https://blog.metabrainz.org/?p=8915 to understand why ' \
    'we need your email.'

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
        "spotify": get_current_spotify_user(),
        "youtube": get_current_youtube_user(),
        "critiquebrainz": get_current_critiquebrainz_user(),
        "musicbrainz": get_current_musicbrainz_user(),
        "soundcloud": get_current_soundcloud_user(),
        "appleMusic": get_current_apple_music_user(),
        "sentry_traces_sample_rate": sentry_config.get("traces_sample_rate", 0.0),
    }

    if current_user.is_authenticated:
        brainzplayer_props = db_usersetting.get_brainzplayer_prefs(db_conn, current_user.id)
        if brainzplayer_props is not None:
            props["user_preferences"] = brainzplayer_props

        flair_props = db_usersetting.get_flair(db_conn, current_user.id)
        if flair_props is not None:
            props["flair"] = flair_props

        if meb_conn:
            show_flair = db_donation.is_user_eligible_donor(meb_conn, current_user.id)
            if show_flair is not None:
                props["show_flair"] = show_flair

    return orjson.dumps(props).decode("utf-8")


def parse_boolean_arg(name, default=None):
    from listenbrainz.webserver.errors import APIBadRequest
    value = request.args.get(name)
    if not value:
        return default

    value = value.lower()
    if value not in ["true", "false"]:
        raise APIBadRequest("Invalid %s argument: %s. Must be 'true' or 'false'" % (name, value))

    return True if value == "true" else False
