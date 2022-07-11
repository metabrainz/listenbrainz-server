from flask import Blueprint, request, redirect, render_template, url_for, session, current_app, Markup
from flask_login import login_user, logout_user, login_required
from listenbrainz.webserver.decorators import web_listenstore_needed, web_musicbrainz_needed
from listenbrainz.webserver.login import login_forbidden, provider, User
from listenbrainz.webserver import flash
import listenbrainz.db.user as db_user
import datetime

from listenbrainz.webserver.login.provider import MusicBrainzAuthSessionError, MusicBrainzAuthNoEmailError

login_bp = Blueprint('login', __name__)


@login_bp.route('/')
@web_musicbrainz_needed
@web_listenstore_needed
@login_forbidden
def index():
    return render_template('login/login.html')


@login_bp.route('/musicbrainz/')
@web_musicbrainz_needed
@web_listenstore_needed
@login_forbidden
def musicbrainz():
    session['next'] = request.args.get('next')
    return redirect(provider.get_authentication_uri())


@login_bp.route('/musicbrainz/post/')
@web_musicbrainz_needed
@web_listenstore_needed
@login_forbidden
def musicbrainz_post():
    """Callback endpoint."""

    no_email_warning = Markup('You have not provided an email address. Please provide an '
                              '<a href="https://musicbrainz.org/account/edit">email address</a> ')
    blog_link = Markup('Read this <a href="https://blog.metabrainz.org/?p=8915">blog post</a> '
                       'to understand why we need your email.')

    if provider.validate_post_login():
        try:
            user = provider.get_user()
            if current_app.config["REJECT_NEW_USERS_WITHOUT_EMAIL"] and not user["email"]:
                # existing user without email, show a warning
                flash.warning(no_email_warning + 'to submit listens. ' + blog_link)

            db_user.update_last_login(user["musicbrainz_id"])
            login_user(User.from_dbrow(user),
                       remember=True,
                       duration=datetime.timedelta(current_app.config['SESSION_REMEMBER_ME_DURATION']))
            next = session.get('next')
            if next:
                return redirect(next)
        except MusicBrainzAuthSessionError:
            flash.error("Login failed.")
        except MusicBrainzAuthNoEmailError:
            # new user without email tried to create an account
            flash.error(no_email_warning + 'before creating a ListenBrainz account. ' + blog_link)
    else:
        flash.error("Login failed.")
    return redirect(url_for('index.index'))


@login_bp.route('/logout/')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('index.index'))
