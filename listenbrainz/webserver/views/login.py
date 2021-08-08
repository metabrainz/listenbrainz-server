from flask import Blueprint, request, redirect, render_template, url_for, session, current_app, Markup
from flask_login import login_user, logout_user, login_required
from brainzutils.musicbrainz_db import engine as mb_engine
from listenbrainz.webserver.login import login_forbidden, provider, User
from listenbrainz.webserver import flash
import listenbrainz.db.user as db_user
import datetime

login_bp = Blueprint('login', __name__)


@login_bp.route('/')
@login_forbidden
def index():
    return render_template('login/login.html')


@login_bp.route('/musicbrainz')
@login_forbidden
def musicbrainz():
    session['next'] = request.args.get('next')
    return redirect(provider.get_authentication_uri())


@login_bp.route('/musicbrainz/post')
@login_forbidden
def musicbrainz_post():
    """Callback endpoint."""
    if provider.validate_post_login():
        user = provider.get_user()
        no_email_warning = Markup('You have not provided an email address. Please provide an '
                                  '<a href="https://musicbrainz.org/account/edit">email address</a> ')
        blog_link = Markup('Read this <a href="https://blog.metabrainz.org/?p=8915">blog post</a> '
                           'to understand why we need your email.')

        if not user:  # new user without email tried to create an account
            flash.error(no_email_warning + 'before creating a ListenBrainz account. ' + blog_link)
            return redirect(url_for('index.index'))

        if current_app.config["REJECT_NEW_USERS_WITHOUT_EMAIL"] and not user["email"]:
            # existing user without email, show a warning
            flash.warning(no_email_warning + 'before 1 November 2021, or you will be unable to submit '
                                             'listens. ' + blog_link)

        db_user.update_last_login(user["musicbrainz_id"])
        login_user(User.from_dbrow(user),
                   remember=True,
                   duration=datetime.timedelta(current_app.config['SESSION_REMEMBER_ME_DURATION']))
        next = session.get('next')
        if next:
            return redirect(next)
    else:
        flash.error("Login failed.")
    return redirect(url_for('index.index'))


@login_bp.route('/logout/')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('index.index'))
