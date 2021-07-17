import string
import random

import ujson
from flask import current_app
from flask_login import current_user

from listenbrainz.webserver.views.views_utils import get_current_spotify_user, get_current_youtube_user


REJECT_LISTENS_WITHOUT_EMAIL_ERROR = \
    'The listens were rejected because the user does not has not provided an email. ' \
    'Please visit https://musicbrainz.org/account/edit to add an email address. ' \
    'Read the blog post at https://blog.metabrainz.org/?p=8915 to understand why ' \
    'we need your email.'


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
     - auth details for spotify and youtube if the current user has connected them
     - sentry dsn
     - API url for frontned to connect to.
    """
    current_user_data = {}
    if current_user.is_authenticated:
        current_user_data = {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
            "auth_token": current_user.auth_token,
        }
    spotify_user = get_current_spotify_user()
    youtube_user = get_current_youtube_user()
    props = {
        "api_url": current_app.config["API_URL"],
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn"),
        "current_user": current_user_data,
        "spotify": spotify_user,
        "youtube": youtube_user,
    }
    return ujson.dumps(props)
