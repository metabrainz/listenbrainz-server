import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.webserver.rabbitmq_connection as rabbitmq_connection
import os
import re
import ujson
import zipfile


from datetime import datetime
from flask import Blueprint, render_template, request, url_for, redirect, current_app, make_response
from flask_login import current_user, login_required
from listenbrainz import webserver
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.stats.utils import construct_stats_queue_key
from listenbrainz.webserver import flash
from listenbrainz.webserver.redis_connection import _redis
from listenbrainz.webserver.influx_connection import _influx
from listenbrainz.webserver.utils import sizeof_readable
from listenbrainz.webserver.views.user import _get_user
from listenbrainz.webserver.views.api_tools import convert_backup_to_native_format, insert_payload, validate_listen, \
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
        stats_exist = db_stats.valid_stats_exist(current_user.id)
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


@profile_bp.route("/export", methods=["GET", "POST"])
@login_required
def export_data():
    """ Exporting the data to json """
    if request.method == "POST":
        db_conn = webserver.create_influx(current_app)
        filename = current_user.musicbrainz_id + "_lb-" + datetime.today().strftime('%Y-%m-%d') + ".json"

        # fetch all listens for the user from listenstore by making repeated queries to
        # listenstore until we get all the data
        to_ts = int(time())
        listens = []
        while True:
            batch = db_conn.fetch_listens(current_user.musicbrainz_id, to_ts=to_ts, limit=EXPORT_FETCH_COUNT)
            if not batch:
                break
            listens.extend(batch)
            to_ts = batch[-1].ts_since_epoch  # new to_ts will the the timestamp of the last listen fetched

        # Fetch output and convert it into dict with keys as indexes
        output = []
        for index, obj in enumerate(listens):
            dic = obj.data
            dic['timestamp'] = obj.ts_since_epoch
            dic['release_msid'] = None if obj.release_msid is None else str(obj.release_msid)
            dic['artist_msid'] = None if obj.artist_msid is None else str(obj.artist_msid)
            dic['recording_msid'] = None if obj.recording_msid is None else str(obj.recording_msid)
            output.append(dic)

        response = make_response(ujson.dumps(output))
        response.headers["Content-Disposition"] = "attachment; filename=" + filename
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.mimetype = "text/json"
        return response
    else:
        return render_template("user/export.html", user=current_user)


@profile_bp.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        try:
            f = request.files['file']
            if f.filename == '':
                flash.warning('No file selected.')
                return redirect(request.url)
        except RequestEntityTooLarge:
            raise RequestEntityTooLarge('Maximum filesize upload limit exceeded. File must be <=' +
                                        sizeof_readable(current_app.config['MAX_CONTENT_LENGTH']))
        except:
            raise InternalServerError("Something went wrong. Could not upload the file")

        # Check upload folder
        if 'UPLOAD_FOLDER' not in current_app.config:
            raise InternalServerError("Could not upload the file. Upload folder not specified")
        upload_path = path.join(path.abspath(current_app.config['UPLOAD_FOLDER']), current_user.musicbrainz_id)
        if not path.isdir(upload_path):
            makedirs(upload_path)

        # Write to a file
        filename = path.join(upload_path, secure_filename(f.filename))
        f.save(filename)

        if not zipfile.is_zipfile(filename):
            raise BadRequest('Not a valid zip file.')

        success = failure = 0
        regex = re.compile('json/scrobbles/scrobbles-*')
        try:
            zf = zipfile.ZipFile(filename, 'r')
            files = zf.namelist()
            # Iterate over file that match the regex
            for f in [f for f in files if regex.match(f)]:
                try:
                    # Load listens file
                    jsonlist = ujson.loads(zf.read(f))
                    if not isinstance(jsonlist, list):
                        raise ValueError
                except ValueError:
                    failure += 1
                    continue

                payload = convert_backup_to_native_format(jsonlist)
                for listen in payload:
                    validate_listen(listen, LISTEN_TYPE_IMPORT)
                insert_payload(payload, current_user)
                success += 1
        except Exception:
            raise BadRequest('Not a valid lastfm-backup-file.')
        finally:
            os.remove(filename)

        # reset listen count for user
        db_connection = webserver.influx_connection._influx
        db_connection.reset_listen_count(current_user.musicbrainz_id)

        flash.info('Congratulations! Your listens from %d files have been uploaded successfully.' % success)
    return redirect(url_for("profile.import_data"))


@profile_bp.route('/request-stats', methods=['GET'])
@login_required
def request_stats():
    """ Check if the current user's statistics have been calculated and if not,
        put them in the stats queue for stats_calculator.
    """
    status = _redis.redis.get(construct_stats_queue_key(current_user.musicbrainz_id)) == 'queued'
    if status == 'queued':
        flash.info('You have already been added to the stats calculation queue! Please check back later.')
    elif db_stats.valid_stats_exist(current_user.id):
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
            exchange=current_app.config['STATS_EXCHANGE'],
            queue=current_app.config['STATS_QUEUE'],
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
                flash.error('Error while deleting user %s, please try again later.' % current_user.musicbrainz_id)
                return redirect(url_for('profile.info'))
            return redirect(url_for('index.index'))
        else:
            flash.error('Cannot delete user due to error during authentication, please try again later.')
            return redirect('profile.info')
    else:
        return render_template('profile/delete.html', token=current_user.auth_token)


def delete_user(musicbrainz_id):
    """ Delete a user from ListenBrainz completely.
    First, drops the user's influx measurement and then deletes her from the
    database.

    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user

    Raises:
        NotFound if user isn't present in the database
    """

    #TODO(param): delete user's listens from Google BigQuery
    user = _get_user(musicbrainz_id)
    _influx.delete(user.musicbrainz_id)
    db_user.delete(user.id)
