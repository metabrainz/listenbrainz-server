from flask import Blueprint, render_template, request, url_for, Response, redirect, flash, current_app, jsonify
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound, BadRequest, RequestEntityTooLarge, InternalServerError
from werkzeug.utils import secure_filename
from listenbrainz.webserver.decorators import crossdomain
from datetime import datetime
from time import time
from listenbrainz import webserver
from listenbrainz.webserver import flash
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats
import listenbrainz.config as config
from listenbrainz.db.exceptions import DatabaseException
from flask import make_response
from listenbrainz.webserver.views.api_tools import convert_backup_to_native_format, insert_payload, validate_listen, \
    MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP, LISTEN_TYPE_IMPORT
from listenbrainz.webserver.utils import sizeof_readable
from listenbrainz.webserver.login import User
from listenbrainz.webserver.redis_connection import _redis
from os import path, makedirs
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import ujson
import zipfile
import re
import os
import pytz
import urllib

LISTENS_PER_PAGE = 25
EXPORT_FETCH_COUNT= 5000

user_bp = Blueprint("user", __name__)


@user_bp.route("/<user_name>/scraper.js")
@crossdomain()
def lastfmscraper(user_name):
    """ Fetch the scraper.js with proper variable injecting
    """
    user_token = request.args.get("user_token")
    lastfm_username = request.args.get("lastfm_username")
    if user_token is None or lastfm_username is None:
        raise NotFound
    scraper = render_template(
        "user/scraper.js",
        base_url="{}/1/submit-listens".format(config.BETA_URL),
        import_url="{}/1/latest-import".format(config.BETA_URL),
        user_token=user_token,
        lastfm_username=lastfm_username,
        # need to escape user_name here because other wise jinja doesn't handle usernames with backslashes correctly
        user_name=urllib.parse.quote(user_name),
        profile_url=url_for('user.profile', user_name=user_name),
        lastfm_api_key=current_app.config['LASTFM_API_KEY'],
        lastfm_api_url=current_app.config['LASTFM_API_URL'],
    )
    return Response(scraper, content_type="text/javascript")

@user_bp.route("/resettoken", methods=["GET", "POST"])
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
            except DatabaseException as e:
                flash.error("Something went wrong! Unable to reset token right now.")
        return redirect(url_for("user.import_data"))
    else:
        token = current_user.auth_token
        return render_template(
            "user/resettoken.html",
            token = token,
        )

@user_bp.route("/resetlatestimportts", methods=["GET", "POST"])
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
            except DatabaseException as e:
                flash.error("Something went wrong! Unable to reset latest import timestamp right now.")
        return redirect(url_for("user.import_data"))
    else:
        token = current_user.auth_token
        return render_template(
            "user/resetlatestimportts.html",
            token=token,
        )

@user_bp.route("/<user_name>")
def profile(user_name):
    # Which database to use to showing user listens.
    db_conn = webserver.influx_connection._influx
    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    user = _get_user(user_name)

    try:
        have_listen_count = True
        listen_count = db_conn.get_listen_count_for_user(user_name)
    except (InfluxDBServerError, InfluxDBClientError):
        have_listen_count = False
        listen_count = 0

    # Getting data for current page
    max_ts = request.args.get("max_ts")
    if max_ts is not None:
        try:
            max_ts = int(max_ts)
        except ValueError:
            raise BadRequest("Incorrect timestamp argument max_ts:" % request.args.get("max_ts"))

    min_ts = request.args.get("min_ts")
    if min_ts is not None:
        try:
            min_ts = int(min_ts)
        except ValueError:
            raise BadRequest("Incorrect timestamp argument min_ts:" % request.args.get("min_ts"))

    if max_ts == None and min_ts == None:
        max_ts = int(time())

    args = {}
    if max_ts:
        args['to_ts'] = max_ts
    else:
        args['from_ts'] = min_ts

    listens = []
    for listen in db_conn.fetch_listens(user_name, limit=LISTENS_PER_PAGE, **args):
        # Let's fetch one more listen, so we know to show a next page link or not
        listens.append({
            "track_metadata": listen.data,
            "listened_at": listen.ts_since_epoch,
            "listened_at_iso": listen.timestamp.isoformat() + "Z",
        })

    # Calculate if we need to show next/prev buttons
    previous_listen_ts = None
    next_listen_ts = None
    if listens:
        (min_ts_per_user, max_ts_per_user) = db_conn.get_timestamps_for_user(user_name)
        if min_ts_per_user >= 0:
            if listens[-1]['listened_at'] > min_ts_per_user:
                next_listen_ts = listens[-1]['listened_at']
            else:
                next_listen_ts = None

            if listens[0]['listened_at'] < max_ts_per_user:
                previous_listen_ts = listens[0]['listened_at']
            else:
                previous_listen_ts = None

    # If there are no previous listens then display now_playing
    if not previous_listen_ts:
        playing_now = playing_now_conn.get_playing_now(user_name)
        if playing_now:
            listen = {
                "track_metadata": playing_now.data,
                "playing_now": "true",
            }
            listens.insert(0, listen)

    user_stats = db_stats.get_user_stats(user.id)
    try:
        artist_count = int(user_stats['artists']['count'])
    except (KeyError, TypeError):
        artist_count = 0

    return render_template(
        "user/profile.html",
        user=user,
        listens=listens,
        previous_listen_ts=previous_listen_ts,
        next_listen_ts=next_listen_ts,
        spotify_uri=_get_spotify_uri_for_listens(listens),
        have_listen_count=have_listen_count,
        listen_count=format(int(listen_count), ",d"),
        artist_count=format(artist_count, ",d")
    )


@user_bp.route("/info")
@login_required
def info():
    return render_template(
        "user/info.html",
        user=current_user
    )

@user_bp.route("/import")
@login_required
def import_data():
    """ Displays the import page to user, giving various options """

    # Return error if LASTFM_API_KEY is not given in config.py
    if 'LASTFM_API_KEY' not in current_app.config or current_app.config['LASTFM_API_KEY'] == "":
        return NotFound("LASTFM_API_KEY not specified.")

    alpha_import_status = "NO_REQUEST"
    redis_connection = _redis.redis
    user_key = "{} {}".format(current_app.config['IMPORTER_SET_KEY_PREFIX'], current_user.musicbrainz_id)
    if redis_connection.exists(user_key):
        alpha_import_status = redis_connection.get(user_key)
    return render_template(
        "user/import.html",
        user=current_user,
        alpha_import_status=alpha_import_status,
        scraper_url=url_for(
            "user.lastfmscraper",
            user_name=current_user.musicbrainz_id,
            _external=True,
        ),
    )


@user_bp.route("/export", methods=["GET", "POST"])
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
            to_ts = batch[-1].ts_since_epoch # new to_ts will the the timestamp of the last listen fetched

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


@user_bp.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        try:
            f = request.files['file']
            if f.filename == '':
                flash('No file selected.')
                return redirect(request.url)
        except RequestEntityTooLarge:
            raise RequestEntityTooLarge('Maximum filesize upload limit exceeded. File must be <=' + \
                  sizeof_readable(current_app.config['MAX_CONTENT_LENGTH']))
        except:
            raise InternalServerError("Something went wrong. Could not upload the file")

        # Check upload folder
        if not 'UPLOAD_FOLDER' in current_app.config:
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
        except Exception as e:
            raise BadRequest('Not a valid lastfm-backup-file.')
        finally:
            os.remove(filename)

        # reset listen count for user
        db_connection = webserver.influx_connection._influx
        db_connection.reset_listen_count(current_user.musicbrainz_id)

        flash('Congratulations! Your listens from %d  files have been uploaded successfully.' % (success))
    return redirect(url_for("user.import_data"))


def _get_user(user_name):
    """ Get current username """
    if current_user.is_authenticated() and \
       current_user.musicbrainz_id == user_name:
        return current_user
    else:
        user = db_user.get_by_mb_id(user_name)
        if user is None:
            raise NotFound("Cannot find user: %s" % user_name)
        return User.from_dbrow(user)


def _get_spotify_uri_for_listens(listens):

    def get_track_id_from_listen(listen):
        additional_info = listen["track_metadata"]["additional_info"]
        if "spotify_id" in additional_info:
            return additional_info["spotify_id"].rsplit('/', 1)[-1]
        else:
            return None

    track_ids = [get_track_id_from_listen(l) for l in listens]
    track_ids = [t_id for t_id in track_ids if t_id]

    if track_ids:
        return "spotify:trackset:Recent listens:" + ",".join(track_ids)
    else:
        return None

@user_bp.route("/import/alpha")
@login_required
def import_from_alpha():
    """ Just push the task into redis queue and then return to user page.
    """
    redis_connection = _redis.redis
    # push into the queue
    value = "{} {}".format(current_user.auth_token, current_user.musicbrainz_id)
    redis_connection.rpush(current_app.config['IMPORTER_QUEUE_KEY'], value)

    # push username into redis so that we know that this user is in waiting
    redis_connection.set("{} {}".format(current_app.config['IMPORTER_SET_KEY_PREFIX'], current_user.musicbrainz_id), "WAITING")
    return redirect(url_for("user.import_data"))
