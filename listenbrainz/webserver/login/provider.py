from flask import request, session, current_app
from brainzutils.musicbrainz_db import engine as mb_engine
from brainzutils.musicbrainz_db import editor as mb_editor

from listenbrainz.domain.musicbrainz import MusicBrainzService, MUSICBRAINZ_SCOPES
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.utils import generate_string
from listenbrainz.webserver.timescale_connection import _ts as ts
import listenbrainz.db.user as db_user

_session_key = "musicbrainz"


class MusicBrainzAuthSessionError(Exception):
    """Raised when there is an error parsing the oauth response from MusicBrainz"""
    pass


class MusicBrainzAuthNoEmailError(Exception):
    """Raised when a user has no email address on MusicBrainz"""
    pass


def get_user():
    """Function should fetch user data from database, or, if necessary, create it, and return it."""
    service = MusicBrainzService()
    try:
        code = _fetch_data("code")
        token = service.fetch_access_token(code)
        info = service.get_user_info(token["access_token"])
        musicbrainz_id = info["sub"]
        musicbrainz_row_id = info["metabrainz_user_id"]
    except KeyError:
        # get_auth_session raises a KeyError if it was unable to get the required data from `code`
        raise MusicBrainzAuthSessionError()

    user = db_user.get_by_mb_row_id(db_conn, musicbrainz_row_id, musicbrainz_id)
    user_email = None
    if mb_engine:
        user_email = mb_editor.get_editor_by_id(musicbrainz_row_id)["email"]

    if user is None:  # a new user is trying to sign up
        if current_app.config["REJECT_NEW_USERS_WITHOUT_EMAIL"] and user_email is None:
            # if flag is set to True and the user does not have an email do not allow to sign up
            raise MusicBrainzAuthNoEmailError()
        db_user.create(db_conn, musicbrainz_row_id, musicbrainz_id, email=user_email)
        user = db_user.get_by_mb_id(db_conn, musicbrainz_id, fetch_email=True)
        ts.set_empty_values_for_user(user["id"])
        # add new oauth token for the user
        service.add_new_user(user["id"], token)
    else:  # an existing user is trying to log in
        # Other option is to change the return type of get_by_mb_row_id to a dict
        # but its used so widely that we would modify huge number of tests
        user = dict(user)
        user["email"] = user_email
        # every time a user logs in, update the email in LB.
        db_user.update_user_details(db_conn, user["id"], musicbrainz_id, user_email)
        # update oauth token for the user
        service.update_user(user["id"], token)

    return user


def get_authentication_uri():
    """Prepare and return URL to authentication service login form."""
    csrf = generate_string(20)
    _persist_data(csrf=csrf)
    return MusicBrainzService().get_authorize_url(MUSICBRAINZ_SCOPES, state=csrf, access_type="offline")


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
