from __future__ import absolute_import
from flask import Blueprint, render_template, request, url_for, Response, redirect, flash, current_app
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound, BadRequest, RequestEntityTooLarge, InternalServerError
from werkzeug.utils import secure_filename
from webserver.decorators import crossdomain
from datetime import datetime
import webserver
import db.user
from flask import make_response
from webserver.views.api_tools import convert_backup_to_native_format, insert_payload, MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP
from webserver.utils import sizeof_readable
from webserver.login import User
from os import path, makedirs
import ujson
import zipfile
import re
import os
import pytz

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
        base_url=url_for("api_v1.submit_listen", user_name=user_name, _external=True),
        user_token=user_token,
        lastfm_username=lastfm_username,
        user_name=user_name,
        lastfm_api_key=current_app.config['LASTFM_API_KEY'],
    )
    return Response(scraper, content_type="text/javascript")


@user_bp.route("/<user_name>")
def profile(user_name):
    # Which database to use to showing user listens.
    db_conn = webserver.postgres_connection._postgres
    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    user = _get_user(user_name)

    # Getting data for current page
    max_ts = request.args.get("max_ts")
    if max_ts is not None:
        try:
            max_ts = int(float(max_ts))
        except ValueError:
            raise BadRequest("Incorrect timestamp argument to_ts:" %
                             request.args.get("to_ts"))
    listens = []
    for listen in db_conn.fetch_listens(user.id, limit=25, to_ts=max_ts):
        listens.append({
            "track_metadata": listen.data,
            "listened_at": listen.ts_since_epoch,
            "listened_at_iso": listen.timestamp.isoformat() + "Z",
        })

    if listens:
        # Checking if there is a "previous" page...
        previous_listens = db_conn.fetch_listens(user.id, limit=25, from_ts=listens[0]["listened_at"])
        if previous_listens:
            # Getting from the last item because `fetch_listens` returns in ascending
            # order when `from_ts` is used.
            previous_listen_ts = previous_listens[-1].timestamp + 1
        else:
            previous_listen_ts = None

        # Checking if there is a "next" page...
        next_listens = db_conn.fetch_listens(user.id, limit=1, to_ts=listens[-1]["listened_at"])
        if next_listens:
            next_listen_ts = listens[-1]["listened_at"]
        else:
            next_listen_ts = None

    else:
        previous_listen_ts = None
        next_listen_ts = None

    # If there are no previous listens then display now_playing
    if not previous_listen_ts:
        playing_now = playing_now_conn.get_playing_now(str(user.id))
        if playing_now:
            listen = {
                "track_metadata": playing_now.data,
                "playing_now": "true",
            }
            listens.insert(0, listen)

    return render_template(
        "user/profile.html",
        user=user,
        listens=listens,
        previous_listen_ts=previous_listen_ts,
        next_listen_ts=next_listen_ts,
        spotify_uri=_get_spotify_uri_for_listens(listens)
    )


@user_bp.route("/import")
@login_required
def import_data():
    """ Displays the import page to user, giving various options """

    # Return error if LASTFM_API_KEY is not given in config.py
    if 'LASTFM_API_KEY' not in current_app.config or current_app.config['LASTFM_API_KEY'] == "":
        return NotFound("LASTFM_API_KEY not specified.")

    lastfm_username = request.args.get("lastfm_username")
    if lastfm_username:
        loader = render_template(
            "user/loader.js",
            base_url=url_for("user.lastfmscraper",
                             user_name=current_user.musicbrainz_id,
                             _external=True),
            user_token=current_user.auth_token,
            lastfm_username=lastfm_username,
        )
        loader = "javascript:%s" % loader
    else:
        loader = None
    return render_template("user/import.html", user=current_user,
            loader=loader, lastfm_username=lastfm_username)


@user_bp.route("/export", methods=["GET", "POST"])
@login_required
def export_data():
    """ Exporting the data to json """
    if request.method == "POST":
        db_conn = webserver.create_postgres(current_app)
        filename = current_user.musicbrainz_id + "_lb-" + datetime.today().strftime('%Y-%m-%d') + ".json"

        # Fetch output and convert it into dict with keys as indexes
        output = []
        for index, obj in enumerate(db_conn.fetch_listens(current_user.id)):
            dic = obj.data
            dic['timestamp'] = obj.ts_since_epoch
            dic['album_msid'] = None if obj.album_msid is None else str(obj.album_msid)
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
                insert_payload(payload, current_user.id)
                success += 1
        except Exception, e:
            raise BadRequest('Not a valid lastfm-backup-file.')
        finally:
            os.remove(filename)
        flash('Congratulations! Your listens from %d  files have been uploaded successfully.' % (success))
    return redirect(url_for("user.import_data"))


def _get_user(user_name):
    """ Get current username """
    if current_user.is_authenticated() and \
       current_user.musicbrainz_id == user_name:
        return current_user
    else:
        user = db.user.get_by_mb_id(user_name)
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
