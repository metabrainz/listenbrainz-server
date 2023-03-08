from datetime import datetime
from time import time

import orjson
from flask import Blueprint, Response, render_template, request, url_for, \
    redirect, current_app, jsonify, stream_with_context
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from werkzeug.exceptions import NotFound, BadRequest

import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.user as db_user
import listenbrainz.db.user_setting as db_usersetting
from data.model.external_service import ExternalServiceType
from listenbrainz.db import listens_importer
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService, CRITIQUEBRAINZ_SCOPES
from listenbrainz.domain.external_service import ExternalService, ExternalServiceInvalidGrantError
from listenbrainz.domain.spotify import SpotifyService, SPOTIFY_LISTEN_PERMISSIONS, SPOTIFY_IMPORT_PERMISSIONS
from listenbrainz.webserver import flash
from listenbrainz.webserver import timescale_connection
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.errors import APIServiceUnavailable, APINotFound
from listenbrainz.webserver.login import api_login_required
from listenbrainz.webserver.views.user import delete_user, delete_listens_history


profile_bp = Blueprint("profile", __name__)

EXPORT_FETCH_COUNT = 5000


@profile_bp.route("/resettoken/", methods=["GET", "POST"])
@login_required
def reset_token():
    form = FlaskForm()
    if form.validate_on_submit():
        try:
            db_user.update_token(current_user.id)
            flash.info("Access token reset")
        except DatabaseException:
            flash.error("Something went wrong! Unable to reset token right now.")
        return redirect(url_for("profile.info"))

    if form.csrf_token.errors:
        flash.error('Cannot reset token due to error during authentication, please try again later.')
        return redirect(url_for('profile.info'))

    return render_template(
        "user/resettoken.html",
        form=form,
    )


@profile_bp.route("/select_timezone/", methods=["GET", "POST"])
@login_required
def select_timezone():
    pg_timezones = db_usersetting.get_pg_timezone()
    user_settings = db_usersetting.get(current_user.id)
    user_timezone = user_settings['timezone_name']
    props = {
        "pg_timezones": pg_timezones,
        "user_timezone": user_timezone,
    }
    return render_template(
        "profile/selecttimezone.html",
        props=orjson.dumps(props).decode("utf-8"),
    )


@profile_bp.route("/troi/", methods=["GET", "OPTIONS"])
@login_required
def set_troi_prefs():
    current_troi_prefs = db_usersetting.get_troi_prefs(current_user.id)
    return render_template(
        "profile/troi_prefs.html",
        props=orjson.dumps({"troi_prefs": current_troi_prefs}).decode("utf-8")
    )


@profile_bp.route("/resetlatestimportts/", methods=["GET", "POST"])
@login_required
def reset_latest_import_timestamp():
    form = FlaskForm()
    if form.validate_on_submit():
        try:
            listens_importer.update_latest_listened_at(current_user.id, ExternalServiceType.LASTFM, 0)
            flash.info("Latest import time reset, we'll now import all your data instead of stopping at your last imported listen.")
        except DatabaseException:
            flash.error("Something went wrong! Unable to reset latest import timestamp right now.")
        return redirect(url_for("profile.info"))

    if form.csrf_token.errors:
        flash.error('Cannot reset import time due to error during authentication, please try again later.')
        return redirect(url_for('profile.info'))

    return render_template(
        "profile/resetlatestimportts.html",
        form=form,
    )


@profile_bp.route("/")
@login_required
def info():

    user_setting = db_usersetting.get(current_user.id)
    return render_template(
        "profile/info.html",
        user=current_user,
        user_setting=user_setting,
    )


@profile_bp.route("/import/")
@login_required
def import_data():
    """ Displays the import page to user, giving various options """
    user = db_user.get(current_user.id, fetch_email=True)
    # if the flag is turned off (local development) then do not perform email check
    if current_app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"]:
        user_has_email = user["email"] is not None
    else:
        user_has_email = True

    # Return error if LASTFM_API_KEY is not given in config.py
    if 'LASTFM_API_KEY' not in current_app.config or current_app.config['LASTFM_API_KEY'] == "":
        return NotFound("LASTFM_API_KEY not specified.")

    user_data = {
        "id": current_user.id,
        "name": current_user.musicbrainz_id,
        "auth_token": current_user.auth_token,
    }

    props = {
        "user": user_data,
        "profile_url": url_for('user.profile', user_name=user_data["name"]),
        "lastfm_api_url": current_app.config["LASTFM_API_URL"],
        "lastfm_api_key": current_app.config["LASTFM_API_KEY"],
        "librefm_api_url": current_app.config["LIBREFM_API_URL"],
        "librefm_api_key": current_app.config["LIBREFM_API_KEY"],
    }

    return render_template(
        "user/import.html",
        user=current_user,
        user_has_email=user_has_email,
        props=orjson.dumps(props).decode("utf-8"),
    )


def fetch_listens(musicbrainz_id, to_ts):
    """
    Fetch all listens for the user from listenstore by making repeated queries
    to listenstore until we get all the data. Returns a generator that streams
    the results.
    """
    while True:
        batch, _, _ = timescale_connection._ts.fetch_listens(current_user.to_dict(), to_ts=to_ts, limit=EXPORT_FETCH_COUNT)
        if not batch:
            break
        yield from batch
        to_ts = batch[-1].ts_since_epoch  # new to_ts will be the the timestamp of the last listen fetched


def fetch_feedback(user_id):
    """
    Fetch feedback by making repeated queries to DB until we get all the data.
    Returns a generator that streams the results.
    """
    batch = []
    offset = 0
    while True:
        batch = db_feedback.get_feedback_for_user(user_id=current_user.id, limit=EXPORT_FETCH_COUNT, offset=offset)
        if not batch:
            break
        yield from batch
        offset += len(batch)


def stream_json_array(elements):
    """ Return a generator of string fragments of the elements encoded as array. """
    for i, element in enumerate(elements):
        yield '[' if i == 0 else ','
        yield orjson.dumps(element).decode("utf-8")
    yield ']'


@profile_bp.route("/export/", methods=["GET", "POST"])
@login_required
@web_listenstore_needed
def export_data():
    """ Exporting the data to json """
    if request.method == "POST":
        filename = current_user.musicbrainz_id + "_lb-" + datetime.today().strftime('%Y-%m-%d') + ".json"

        # Build a generator that streams the json response. We never load all
        # listens into memory at once, and we can start serving the response
        # immediately.
        to_ts = int(time())
        listens = fetch_listens(current_user.musicbrainz_id, to_ts)
        output = stream_json_array(listen.to_api() for listen in listens)

        response = Response(stream_with_context(output))
        response.headers["Content-Disposition"] = "attachment; filename=" + filename
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.mimetype = "text/json"
        return response
    else:
        return render_template("user/export.html", user=current_user)


@profile_bp.route("/export-feedback/", methods=["POST"])
@login_required
def export_feedback():
    """ Exporting the feedback data to json """
    filename = current_user.musicbrainz_id + "_lb_feedback-" + datetime.today().strftime('%Y-%m-%d') + ".json"

    # Build a generator that streams the json response. We never load all
    # feedback into memory at once, and we can start serving the response
    # immediately.
    feedback = fetch_feedback(current_user.id)
    output = stream_json_array(fb.to_api() for fb in feedback)

    response = Response(stream_with_context(output))
    response.headers["Content-Disposition"] = "attachment; filename=" + filename
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.mimetype = "text/json"
    return response


@profile_bp.route('/delete/', methods=['GET', 'POST'])
@login_required
@web_listenstore_needed
def delete():
    """ Delete currently logged-in user from ListenBrainz.

    If POST request, this view checks for the correct authorization token and
    deletes the user. If deletion is successful, redirects to home page, else
    flashes an error and redirects to user's info page.

    If GET request, this view renders a page asking the user to confirm
    that they wish to delete their ListenBrainz account.
    """
    form = FlaskForm()
    if form.validate_on_submit():
        try:
            delete_user(current_user.id)
            flash.success("Successfully deleted account for %s." % current_user.musicbrainz_id)
            return redirect(url_for('index.index'))
        except Exception:
            current_app.logger.error('Error while deleting user: %s', current_user.musicbrainz_id, exc_info=True)
            flash.error('Error while deleting user %s, please try again later.' % current_user.musicbrainz_id)
            return redirect(url_for('profile.info'))

    if form.csrf_token.errors:
        flash.error('Cannot delete user due to error during authentication, please try again later.')
        return redirect(url_for('profile.info'))

    return render_template(
        'profile/delete.html',
        user=current_user,
        form=form
    )


@profile_bp.route('/delete-listens/', methods=['GET', 'POST'])
@login_required
@web_listenstore_needed
def delete_listens():
    """ Delete all the listens for the currently logged-in user from ListenBrainz.

    If POST request, this view checks for the correct authorization token and
    deletes the listens. If deletion is successful, redirects to user's profile page,
    else flashes an error and redirects to user's info page.

    If GET request, this view renders a page asking the user to confirm that they
    wish to delete their listens.
    """
    form = FlaskForm()
    if form.validate_on_submit():
        try:
            delete_listens_history(current_user.id)
            flash.info('Successfully deleted listens for %s.' % current_user.musicbrainz_id)
            return redirect(url_for('user.profile', user_name=current_user.musicbrainz_id))
        except Exception:
            current_app.logger.error('Error while deleting listens for user: %s', current_user.musicbrainz_id, exc_info=True)
            flash.error('Error while deleting listens for %s, please try again later.' % current_user.musicbrainz_id)
            return redirect(url_for('profile.info'))

    if form.csrf_token.errors:
        flash.error('Cannot delete listens due to error during authentication, please try again later.')
        return redirect(url_for('profile.info'))

    return render_template(
        'profile/delete_listens.html',
        user=current_user,
        form=form
    )


def _get_service_or_raise_404(name: str) -> ExternalService:
    """Returns the music service for the given name and raise 404 if
    service is not found

    Args:
        name (str): Name of the service
    """
    try:
        service = ExternalServiceType[name.upper()]
        if service == ExternalServiceType.SPOTIFY:
            return SpotifyService()
        elif service == ExternalServiceType.CRITIQUEBRAINZ:
            return CritiqueBrainzService()
    except KeyError:
        raise NotFound("Service %s is invalid." % name)


@profile_bp.route('/music-services/details/', methods=['GET'])
@login_required
def music_services_details():
    spotify_service = SpotifyService()
    spotify_user = spotify_service.get_user(current_user.id)

    if spotify_user:
        permissions = set(spotify_user["scopes"])
        if permissions == SPOTIFY_IMPORT_PERMISSIONS:
            current_spotify_permissions = "import"
        elif permissions == SPOTIFY_LISTEN_PERMISSIONS:
            current_spotify_permissions = "listen"
        else:
            current_spotify_permissions = "both"
    else:
        current_spotify_permissions = "disable"

    critiquebrainz_service = CritiqueBrainzService()
    critiquebrainz_user = critiquebrainz_service.get_user(current_user.id)
    current_critiquebrainz_permissions = "review" if critiquebrainz_user else "disable"

    return render_template(
        'user/music_services.html',
        spotify_user=spotify_user,
        current_spotify_permissions=current_spotify_permissions,
        critiquebrainz_user=critiquebrainz_user,
        current_critiquebrainz_permissions=current_critiquebrainz_permissions
    )


@profile_bp.route('/music-services/<service_name>/callback/')
@login_required
def music_services_callback(service_name: str):
    service = _get_service_or_raise_404(service_name)
    code = request.args.get('code')
    if not code:
        raise BadRequest('missing code')
    token = service.fetch_access_token(code)
    if service.add_new_user(current_user.id, token):
        flash.success('Successfully authenticated with %s!' % service_name.capitalize())
    else:
        flash.error('Unable to connect to %s! Please try again.' % service_name.capitalize())
    return redirect(url_for('profile.music_services_details'))


@profile_bp.route('/music-services/<service_name>/refresh/', methods=['POST'])
@api_login_required
def refresh_service_token(service_name: str):
    service = _get_service_or_raise_404(service_name)
    user = service.get_user(current_user.id)
    if not user:
        raise APINotFound("User has not authenticated to %s" % service_name.capitalize())

    if service.user_oauth_token_has_expired(user):
        try:
            user = service.refresh_access_token(current_user.id, user["refresh_token"])
        except ExternalServiceInvalidGrantError:
            raise APINotFound("User has revoked authorization to %s" % service_name.capitalize())
        except Exception:
            raise APIServiceUnavailable("Cannot refresh %s token right now" % service_name.capitalize())

    return jsonify({"access_token": user["access_token"]})


@profile_bp.route('/music-services/<service_name>/disconnect/', methods=['POST'])
@api_login_required
def music_services_disconnect(service_name: str):
    service = _get_service_or_raise_404(service_name)
    user = service.get_user(current_user.id)
    # this is to support the workflow of changing permissions in a single step
    # we delete the current permissions and then try to authenticate with new ones
    # we should try to delete the current permissions only if the user has connected previously
    if user:
        service.remove_user(current_user.id)

    action = request.form.get(service_name)
    if not action or action == 'disable':
        flash.success('Your %s account has been unlinked.' % service_name.capitalize())
        return redirect(url_for('profile.music_services_details'))
    else:
        if service_name == 'spotify':
            permissions = None
            if action == 'both':
                permissions = SPOTIFY_LISTEN_PERMISSIONS | SPOTIFY_IMPORT_PERMISSIONS
            elif action == 'import':
                permissions = SPOTIFY_IMPORT_PERMISSIONS
            elif action == 'listen':
                permissions = SPOTIFY_LISTEN_PERMISSIONS
            if permissions:
                return redirect(service.get_authorize_url(permissions))
        elif service_name == 'critiquebrainz':
            action = request.form.get('critiquebrainz')
            if action:
                return redirect(service.get_authorize_url(CRITIQUEBRAINZ_SCOPES))

    return redirect(url_for('profile.music_services_details'))
