import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.webserver.rabbitmq_connection as rabbitmq_connection
from listenbrainz.webserver.decorators import crossdomain
import os
import re
import ujson
import zipfile


from datetime import datetime
from flask import Blueprint, Response, render_template, request, url_for, \
    redirect, current_app, make_response, jsonify, stream_with_context
from flask_login import current_user, login_required
import spotipy.oauth2
from werkzeug.exceptions import NotFound, BadRequest, RequestEntityTooLarge, InternalServerError
from listenbrainz.webserver.errors import APIBadRequest, APIServiceUnavailable, APINotFound
from werkzeug.utils import secure_filename

from listenbrainz import webserver
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.domain import spotify
from listenbrainz.stats.utils import construct_stats_queue_key
from listenbrainz.webserver import flash
from listenbrainz.webserver.login import api_login_required
from listenbrainz.webserver.redis_connection import _redis
from listenbrainz.webserver.influx_connection import _influx
from listenbrainz.webserver.utils import sizeof_readable
from listenbrainz.webserver.views.user import delete_user, _get_user, delete_listens_history
from listenbrainz.webserver.views.api_tools import insert_payload, validate_listen, \
    LISTEN_TYPE_IMPORT, publish_data_to_queue
from os import path, makedirs
from time import time
from werkzeug.exceptions import NotFound, BadRequest, RequestEntityTooLarge, InternalServerError
from werkzeug.utils import secure_filename

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

    # check if user is in stats calculation queue or if valid stats already exist
    in_stats_queue = _redis.redis.get(construct_stats_queue_key(current_user.musicbrainz_id)) == 'queued'
    try:
        stats_exist = db_stats.valid_stats_exist(current_user.id, current_app.config['STATS_CALCULATION_INTERVAL'])
    except DatabaseException:
        stats_exist = False

    return render_template(
        "profile/info.html",
        user=current_user,
        in_stats_queue=in_stats_queue,
        stats_exist=stats_exist,
    )


@profile_bp.route("/import")
@login_required
def import_data():
    """ Displays the import page to user, giving various options """

    # Return error if LASTFM_API_KEY is not given in config.py
    if 'LASTFM_API_KEY' not in current_app.config or current_app.config['LASTFM_API_KEY'] == "":
        return NotFound("LASTFM_API_KEY not specified.")

    return render_template(
        "user/import.html",
        user=current_user,
        scraper_url=url_for(
            "user.lastfmscraper",
            user_name=current_user.musicbrainz_id,
            _external=True,
        ),
    )


def fetch_listens(musicbrainz_id, to_ts):
    """
    Fetch all listens for the user from listenstore by making repeated queries
    to listenstore until we get all the data. Returns a generator that streams
    the results.
    """
    db_conn = webserver.create_influx(current_app)
    while True:
        batch = db_conn.fetch_listens(current_user.musicbrainz_id, to_ts=to_ts, limit=EXPORT_FETCH_COUNT)
        if not batch:
            break
        yield from batch
        to_ts = batch[-1].ts_since_epoch  # new to_ts will be the the timestamp of the last listen fetched


def stream_json_array(elements):
    """ Return a generator of string fragments of the elements encoded as array. """
    for i, element in enumerate(elements):
        yield '[' if i == 0 else ','
        yield ujson.dumps(element)
    yield ']'


@profile_bp.route("/export", methods=["GET", "POST"])
@login_required
def export_data():
    """ Exporting the data to json """
    if request.method == "POST":
        db_conn = webserver.create_influx(current_app)
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


@profile_bp.route('/request-stats', methods=['GET'])
@login_required
def request_stats():
    """ Check if the current user's statistics have been calculated and if not,
        put them in the stats queue for stats_calculator.
    """
    status = _redis.redis.get(construct_stats_queue_key(current_user.musicbrainz_id)) == 'queued'
    if status == 'queued':
        flash.info('You have already been added to the stats calculation queue! Please check back later.')
    elif db_stats.valid_stats_exist(current_user.id, current_app.config['STATS_CALCULATION_INTERVAL']):
        flash.info('Your stats were calculated in the most recent stats calculation interval,'
            ' please wait until the next interval! We calculate new statistics every Monday at 00:00 UTC.')
    else:
        # publish to rabbitmq queue that the stats-calculator consumes
        data = {
            'type': 'user',
            'id': current_user.id,
            'musicbrainz_id': current_user.musicbrainz_id,
        }
        publish_data_to_queue(
            data=data,
            exchange=current_app.config['BIGQUERY_EXCHANGE'],
            queue=current_app.config['BIGQUERY_QUEUE'],
            error_msg='Could not put user %s into statistics calculation queue, please try again later',
        )
        _redis.redis.set(construct_stats_queue_key(current_user.musicbrainz_id), 'queued')
        flash.info('You have been added to the stats calculation queue! Please check back later.')
    return redirect(url_for('profile.info'))


@profile_bp.route('/delete', methods=['GET', 'POST'])
@login_required
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
            return redirect('profile.info')
    else:
        return render_template(
            'profile/delete.html',
            user=current_user,
        )

@profile_bp.route('/delete-listens', methods=['GET', 'POST'])
@login_required
def delete_listens():
    """ Delete all the listens for the currently logged-in user from ListenBrainz.

    If POST request, this view checks for the correct authorization token and
    deletes the listens. If deletion is successful, redirects to user's profile page, 
    else flashes an error and redirects to user's info page.

    If GET request, this view renders a page asking the user to confirm
    that they wish to delete their listens.
    """
    if request.method == 'POST':
        if request.form.get('token') == current_user.auth_token:
            try:
                delete_listens_history(current_user.musicbrainz_id)
            except Exception as e:
                current_app.logger.error('Error while deleting listens for %s: %s', current_user.musicbrainz_id, str(e))
                flash.error('Error while deleting listens for %s, please try again later.' % current_user.musicbrainz_id)
                return redirect(url_for('profile.info'))
            flash.info('Successfully deleted listens for %s.' % current_user.musicbrainz_id)
            return redirect(url_for('user.profile', user_name=current_user.musicbrainz_id))
        else:
            flash.error('Cannot delete the user\'s listens due to error during authentication, please try again later.')
            return redirect('profile.info')
    else:
        return render_template(
            'profile/deletelistens.html',
            user=current_user,
        )

@profile_bp.route('/connect-spotify', methods=['GET', 'POST'])
@login_required
def connect_spotify():
    if request.method == 'POST' and request.form.get('delete') == 'yes':
        spotify.remove_user(current_user.id)
        flash.success('Your Spotify account has been unlinked')

    user = spotify.get_user(current_user.id)
    only_listen_sp_oauth = spotify.get_spotify_oauth(spotify.SPOTIFY_LISTEN_PERMISSIONS)
    only_import_sp_oauth = spotify.get_spotify_oauth(spotify.SPOTIFY_IMPORT_PERMISSIONS)
    both_sp_oauth = spotify.get_spotify_oauth(spotify.SPOTIFY_LISTEN_PERMISSIONS + spotify.SPOTIFY_IMPORT_PERMISSIONS)

    return render_template(
        'user/spotify.html',
        account=user,
        last_updated=user.last_updated_iso if user else None,
        latest_listened_at=user.latest_listened_at_iso if user else None,
        only_listen_url=only_listen_sp_oauth.get_authorize_url(),
        only_import_url=only_import_sp_oauth.get_authorize_url(),
        both_url=both_sp_oauth.get_authorize_url(),
    )


@profile_bp.route('/connect-spotify/callback')
@login_required
def connect_spotify_callback():
    code = request.args.get('code')
    if not code:
        raise BadRequest('missing code')

    try:
        token = spotify.get_access_token(code)
        spotify.add_new_user(current_user.id, token)
        flash.success('Successfully authenticated with Spotify!')
    except spotipy.oauth2.SpotifyOauthError as e:
        current_app.logger.error('Unable to authenticate with Spotify: %s', str(e), exc_info=True)
        flash.warn('Unable to authenticate with Spotify (error {})'.format(e.args[0]))

    return redirect(url_for('profile.connect_spotify'))


@profile_bp.route('/refresh-spotify-token', methods=['POST'])
@crossdomain()
@api_login_required
def refresh_spotify_token():
    spotify_user = spotify.get_user(current_user.id)
    if not spotify_user:
        raise APINotFound("User has not authenticated to Spotify")
    if spotify_user.token_expired:
        try:
            spotify_user = spotify.refresh_user_token(spotify_user)
        except spotify.SpotifyAPIError:
            raise APIServiceUnavailable("Cannot refresh Spotify token right now")

    return jsonify({
        'id': current_user.id,
        'musicbrainz_id': current_user.musicbrainz_id,
        'user_token': spotify_user.user_token,
        'permission': spotify_user.permission,
    })
