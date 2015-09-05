from __future__ import absolute_import
from flask import Blueprint, request, redirect, render_template, url_for, session
from flask_login import login_user, logout_user, login_required
from webserver.login import login_forbidden, provider
from webserver import flash

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
        login_user(provider.get_user())
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
