from flask import current_app, request, session
import requests

from listenbrainz.domain.musicbrainz import MusicBrainzService, MUSICBRAINZ_SCOPES
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.utils import generate_string
from listenbrainz.webserver.timescale_connection import _ts as ts
import listenbrainz.db.user as db_user

_session_key = "musicbrainz"
LOGIN_HINTS = {"login", "register"}


class MusicBrainzAuthSessionError(Exception):
    """Raised when there is an error parsing the oauth response from MusicBrainz"""
    pass


def get_user():
    """Function should fetch user data from database, or, if necessary, create it, and return it."""
    service = MusicBrainzService()
    try:
        code = _fetch_data("code")
        token = service.fetch_access_token(code)
        info = service.get_user_info(token["access_token"])
        musicbrainz_id = info["username"]
        musicbrainz_row_id = info["sub"]
    except KeyError as e:
        # get_auth_session raises a KeyError if it was unable to get the required data from `code`
        current_app.logger.error("Error occurred while validating MetaBrainz user introspection: %s", str(e))
        raise MusicBrainzAuthSessionError()

    user = db_user.get_by_mb_row_id(db_conn, musicbrainz_row_id, musicbrainz_id, fetch_email=True)

    if user is None:
        email = _get_new_user_email(service, token["access_token"], musicbrainz_row_id)
        db_user.create(
            db_conn,
            musicbrainz_row_id,
            musicbrainz_id,
            email=email,
        )
        user = db_user.get_by_mb_id(db_conn, musicbrainz_id, fetch_email=True)
        ts.set_empty_values_for_user(user["id"])

    # save user's MB OAuth token, this check cannot be merged with the previous signup/login check because
    # we have a different service user row for each LB deployment but a common user row for all three
    if service.get_user(user["id"]) is None:
        service.add_new_user(user["id"], token)
    else:
        service.update_user(user["id"], token)

    return user


def _get_new_user_email(service: MusicBrainzService, token: str, musicbrainz_row_id: int):
    """Return a new user's verified email from OAuth UserInfo."""
    try:
        info = service.get_user_profile(token)
    except requests.RequestException as error:
        current_app.logger.error("Unable to fetch email from MetaBrainz OAuth UserInfo", exc_info=True)
        raise MusicBrainzAuthSessionError() from error

    has_email = "email" in info
    has_email_verified = "email_verified" in info
    if not has_email and not has_email_verified:
        return None

    return info["email"] if info["email_verified"] is True else None


def get_authentication_uri(login_hint=None):
    """Prepare and return URL to authentication service login form."""
    csrf = generate_string(20)
    _persist_data(csrf=csrf)
    kwargs = {
        "state": csrf,
        "access_type": "offline",
    }
    if login_hint in LOGIN_HINTS:
        kwargs["login_hint"] = login_hint
    return MusicBrainzService().get_authorize_url(MUSICBRAINZ_SCOPES, **kwargs)


def validate_post_login():
    """Function validating parameters passed in uri query after redirection from login form.
    Should return True, if everything is ok, or False, if something went wrong.
    """
    if request.args.get('error'):
        return False
    if _fetch_data('csrf') != request.args.get('state'):
        return False
    code = request.args.get('code')
    if not code:
        return False
    _persist_data(code=code)
    return True


def _persist_data(**kwargs):
    """Save data in session."""
    if _session_key not in session:
        session[_session_key] = dict()
    session[_session_key].update(**kwargs)
    session.modified = True


def _fetch_data(key, default=None):
    """Fetch data from session."""
    if _session_key not in session:
        return None
    else:
        return session[_session_key].get(key, default)
