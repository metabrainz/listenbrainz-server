import sqlalchemy

import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.user as db_user
from listenbrainz.webserver.decorators import web_listenstore_needed
from data.model.external_service import ExternalServiceType
from listenbrainz.domain.external_service import ExternalService, ExternalServiceInvalidGrantError
from listenbrainz.domain.spotify import SpotifyService, SPOTIFY_LISTEN_PERMISSIONS, SPOTIFY_IMPORT_PERMISSIONS
from listenbrainz.domain.youtube import YoutubeService, YOUTUBE_SCOPES
from listenbrainz.webserver.decorators import crossdomain
import ujson


from datetime import datetime
from flask import Blueprint, Response, render_template, request, url_for, \
    redirect, current_app, jsonify, stream_with_context
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound, BadRequest, Unauthorized
from listenbrainz.webserver.errors import APIServiceUnavailable, APINotFound, APIBadRequest

from listenbrainz import webserver
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.webserver import flash
from listenbrainz.webserver.login import api_login_required
from listenbrainz.webserver.views.feedback_api import _feedback_to_api
from listenbrainz.webserver.views.user import delete_user, delete_listens_history
from time import time

profile_bp = Blueprint("profile", __name__)

EXPORT_FETCH_COUNT = 5000


@profile_bp.route("/resettoken", methods=["GET", "POST"])
@login_required
def reset_token():
    if request.method == "POST":
        token = request.form.get("token")
        if token != current_user.auth_token:
            raise BadRequest("Can only reset token of currently logged in user")
        reset = request.form.get("reset")
        if reset == "yes":
            try:
                db_user.update_token(current_user.id)
                flash.info("Access token reset")
            except DatabaseException:
                flash.error("Something went wrong! Unable to reset token right now.")
        return redirect(url_for("profile.info"))
    else:
        token = current_user.auth_token
        return render_template(
            "user/resettoken.html",
            token=token,
        )


@profile_bp.route("/resetlatestimportts", methods=["GET", "POST"])
@login_required
def reset_latest_import_timestamp():
    if request.method == "POST":
        token = request.form.get("token")
        if token != current_user.auth_token:
            raise BadRequest("Can only reset latest import timestamp of currently logged in user")
        reset = request.form.get("reset")
        if reset == "yes":
            try:
                db_user.reset_latest_import(current_user.musicbrainz_id)
                flash.info("Latest import time reset, we'll now import all your data instead of stopping at your last imported listen.")
            except DatabaseException:
                flash.error("Something went wrong! Unable to reset latest import timestamp right now.")
        return redirect(url_for("profile.info"))
    else:
        token = current_user.auth_token
        return render_template(
            "profile/resetlatestimportts.html",
            token=token,
        )


@profile_bp.route("/")
@login_required
def info():

    return render_template(
        "profile/info.html",
        user=current_user
    )


@profile_bp.route("/import")
@login_required
def import_data():
    """ Displays the import page to user, giving various options """

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
    }

    return render_template(
        "user/import.html",
        user=current_user,
        props=ujson.dumps(props),
    )


def fetch_listens(musicbrainz_id, to_ts):
    """
    Fetch all listens for the user from listenstore by making repeated queries
    to listenstore until we get all the data. Returns a generator that streams
    the results.
    """
    db_conn = webserver.create_timescale(current_app)
    while True:
        batch, _, _ = db_conn.fetch_listens(current_user.musicbrainz_id, to_ts=to_ts, limit=EXPORT_FETCH_COUNT)
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
        yield ujson.dumps(element)
    yield ']'


@profile_bp.route("/export", methods=["GET", "POST"])
@login_required
@web_listenstore_needed
def export_data():
    """ Exporting the data to json """
    if request.method == "POST":
        db_conn = webserver.create_timescale(current_app)
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


@profile_bp.route("/export-feedback", methods=["POST"])
@login_required
def export_feedback():
    """ Exporting the feedback data to json """
    filename = current_user.musicbrainz_id + "_lb_feedback-" + datetime.today().strftime('%Y-%m-%d') + ".json"

    # Build a generator that streams the json response. We never load all
    # feedback into memory at once, and we can start serving the response
    # immediately.
    feedback = fetch_feedback(current_user.id)
    output = stream_json_array(_feedback_to_api(fb=fb) for fb in feedback)

    response = Response(stream_with_context(output))
    response.headers["Content-Disposition"] = "attachment; filename=" + filename
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.mimetype = "text/json"
    return response


@profile_bp.route('/delete', methods=['GET', 'POST'])
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
    if request.method == 'POST':
        if request.form.get('token') == current_user.auth_token:
            try:
                delete_user(current_user.musicbrainz_id)
            except Exception as e:
                current_app.logger.error('Error while deleting %s: %s', current_user.musicbrainz_id, str(e))
                flash.error('Error while deleting user %s, please try again later.' % current_user.musicbrainz_id)
                return redirect(url_for('profile.info'))
            return redirect(url_for('index.index'))
        else:
            flash.error('Cannot delete user due to error during authentication, please try again later.')
            return redirect(url_for('profile.info'))
    else:
        return render_template(
            'profile/delete.html',
            user=current_user,
        )


@profile_bp.route('/delete-listens', methods=['GET', 'POST'])
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
    if request.method == 'POST':
        if request.form.get('token') and (request.form.get('token') == current_user.auth_token):
            try:
                delete_listens_history(current_user.musicbrainz_id)
            except Exception as e:
                current_app.logger.error('Error while deleting listens for %s: %s', current_user.musicbrainz_id, str(e))
                flash.error('Error while deleting listens for %s, please try again later.' % current_user.musicbrainz_id)
                return redirect(url_for('profile.info'))
            flash.info('Successfully deleted listens for %s.' % current_user.musicbrainz_id)
            return redirect(url_for('user.profile', user_name=current_user.musicbrainz_id))
        else:
            raise Unauthorized("Auth token invalid or missing.")
    else:
        return render_template(
            'profile/delete_listens.html',
            user=current_user,
        )


def _get_service_or_raise_404(name: str) -> ExternalService:
    """Returns the music service for the given name and raise 404 if
    service is not found

    Args:
        name (str): Name of the service
    """
    try:
        service = ExternalServiceType[name.upper()]
        if service == ExternalServiceType.YOUTUBE:
            return YoutubeService()
        elif service == ExternalServiceType.SPOTIFY:
            return SpotifyService()
    except KeyError:
        raise NotFound("Service %s is invalid." % name)


@profile_bp.route('/music-services/details/', methods=['GET'])
@login_required
def music_services_details():
    spotify_service = SpotifyService()
    spotify_user = spotify_service.get_user(current_user.id)

    if spotify_user:
        permissions = set(spotify_user["scopes"])
        if permissions == set(SPOTIFY_IMPORT_PERMISSIONS):
            current_spotify_permissions = "import"
        elif permissions == set(SPOTIFY_LISTEN_PERMISSIONS):
            current_spotify_permissions = "listen"
        else:
            current_spotify_permissions = "both"
    else:
        current_spotify_permissions = "disable"

    youtube_service = YoutubeService()
    youtube_user = youtube_service.get_user(current_user.id)
    current_youtube_permissions = "listen" if youtube_user else "disable"

    return render_template(
        'user/music_services.html',
        spotify_user=spotify_user,
        current_spotify_permissions=current_spotify_permissions,
        youtube_user=youtube_user,
        current_youtube_permissions=current_youtube_permissions
    )


@profile_bp.route('/music-services/<service_name>/callback/')
@login_required
def music_services_callback(service_name: str):
    service = _get_service_or_raise_404(service_name)
    code = request.args.get('code')
    if not code:
        raise BadRequest('missing code')
    token = service.fetch_access_token(code)
    service.add_new_user(current_user.id, token)
    flash.success('Successfully authenticated with %s!' % service_name.capitalize())
    return redirect(url_for('profile.music_services_details'))


@profile_bp.route('/music-services/<service_name>/refresh/', methods=['POST'])
@crossdomain()
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
@crossdomain()
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
                permissions = SPOTIFY_LISTEN_PERMISSIONS + SPOTIFY_IMPORT_PERMISSIONS
            elif action == 'import':
                permissions = SPOTIFY_IMPORT_PERMISSIONS
            elif action == 'listen':
                permissions = SPOTIFY_LISTEN_PERMISSIONS
            if permissions:
                return redirect(service.get_authorize_url(permissions))
        elif service_name == 'youtube':
            action = request.form.get('youtube')
            if action:
                return redirect(service.get_authorize_url(YOUTUBE_SCOPES))

    return redirect(url_for('profile.music_services_details'))
