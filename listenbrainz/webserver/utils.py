import string
import random

import ujson
from flask import current_app
from flask_login import current_user

from listenbrainz.domain import spotify


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


def inject_global_props():
    current_user_data = {}
    spotify_data = {}
    if current_user.is_authenticated:
        current_user_data = {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
            "auth_token": current_user.auth_token,
        }
        spotify_data = spotify.get_user_dict(current_user.id)
    props = {
        "api_url": current_app.config["API_URL"],
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn"),
        "current_user": current_user_data,
        "spotify": spotify_data,
    }
    return ujson.dumps(props)
