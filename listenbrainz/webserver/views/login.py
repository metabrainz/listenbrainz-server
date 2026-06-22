from flask import Blueprint, request, redirect, url_for, session, current_app
from flask_login import login_user, logout_user, login_required
from markupsafe import Markup

from listenbrainz.webserver.decorators import web_listenstore_needed, web_musicbrainz_needed
from listenbrainz.webserver.login import login_forbidden, provider, User
from listenbrainz.webserver import flash, db_conn
import listenbrainz.db.user as db_user
import datetime

from listenbrainz.webserver.login.provider import MusicBrainzAuthSessionError
from listenbrainz.webserver.utils import EMAIL_REQUIRED_BLOG_URL, METABRAINZ_PROFILE_URL

login_bp = Blueprint('login', __name__)


@login_bp.get('/musicbrainz/')
@web_musicbrainz_needed
@web_listenstore_needed
@login_forbidden
def musicbrainz():
    session["next"] = request.args.get("next")
    login_hint = request.args.get("login_hint")
    return redirect(provider.get_authentication_uri(login_hint=login_hint))


@login_bp.get('/musicbrainz/post/')
@web_musicbrainz_needed
@web_listenstore_needed
@login_forbidden
def musicbrainz_post():
    """Callback endpoint."""

    no_email_warning = Markup(
        'Your MetaBrainz account does not have a verified email address. '
        'Please check your inbox for a verification email, or go to your '
        f'<a href="{METABRAINZ_PROFILE_URL}">MetaBrainz profile page</a> to verify your email '
        'before submitting listens or connecting music services. '
        f'Read this <a href="{EMAIL_REQUIRED_BLOG_URL}">blog post</a> '
        'to understand why we need your email.'
    )

    if provider.validate_post_login():
        try:
            user = provider.get_user()
            if current_app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"] and not user["email"]:
                flash.warning(no_email_warning)

            db_user.update_last_login(db_conn, user["musicbrainz_id"])
            login_user(User.from_dbrow(user),
                       remember=True,
                       duration=datetime.timedelta(current_app.config['SESSION_REMEMBER_ME_DURATION']))
            next = session.get('next')
            if next:
                return redirect(next)
        except MusicBrainzAuthSessionError:
            flash.error("Login failed.")
    else:
        flash.error("Login failed.")
    return redirect(url_for('index.index_pages', path=''))


@login_bp.get('/logout/')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('index.index_pages', path=''))
