
from flask import Blueprint, request, redirect, render_template, url_for, session
from flask_login import login_user, logout_user, login_required
from listenbrainz.webserver.login import login_forbidden, provider
from listenbrainz.webserver import flash
import listenbrainz.db.user as db_user
import time

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
        db_user.update_last_login(user.musicbrainz_id)
        login_user(user)
        next = session.get('next')
        if next:
            return redirect(next)
    else:
        flash.error("Login failed.")
    return redirect(url_for('index.index'))


@login_bp.route('/logout/')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index.index'))
