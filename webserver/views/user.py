from __future__ import absolute_import
from flask import Blueprint, render_template, request, url_for, Response, redirect, flash, current_app
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound, BadRequest
from webserver.decorators import crossdomain
from datetime import datetime
import webserver
import db.user
from flask import make_response
from webserver.views.api import _validate_listen, _messybrainz_lookup, _send_listens_to_redis,\
                                _payload_to_augmented_list, MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP
import json

user_bp = Blueprint("user", __name__)

@user_bp.route("/<user_id>/scraper.js")
@crossdomain()
def lastfmscraper(user_id):
    """ Fetch the scraper.js with proper variable injecting
    """
    user_token = request.args.get("user_token")
    lastfm_username = request.args.get("lastfm_username")
    if user_token is None or lastfm_username is None:
        raise NotFound
    scraper = render_template(
        "user/scraper.js",
        base_url=url_for("api_v1.submit_listen", user_id=user_id, _external=True),
        user_token=user_token,
        lastfm_username=lastfm_username,
        user_id=user_id,
        lastfm_api_key=current_app.config['LASTFM_API_KEY'],
    )
    return Response(scraper, content_type="text/javascript")


@user_bp.route("/<user_id>")
def profile(user_id):
    # Which database to use to showing user listens.
    db_conn = webserver.create_postgres()

    # Getting data for current page
    max_ts = request.args.get("max_ts")
    if max_ts is not None:
        try:
            max_ts = int(float(max_ts))
        except ValueError:
            raise BadRequest("Incorrect timestamp argument to_id:" %
                             request.args.get("to_id"))
    listens = []
    for listen in db_conn.fetch_listens(user_id, limit=25, to_id=max_ts):
        listens.append({
            "track_metadata": listen.data,
            "listened_at": listen.timestamp,
            "listened_at_iso": datetime.fromtimestamp(int(listen.timestamp)).isoformat() + "Z",
        })

    if listens:
        # Checking if there is a "previous" page...
        previous_listens = list(db_conn.fetch_listens(user_id, limit=25, from_id=listens[0]["listened_at"]))
        if previous_listens:
            # Getting from the last item because `fetch_listens` returns in ascending
            # order when `from_id` is used.
            previous_listen_ts = previous_listens[-1].timestamp + 1
        else:
            previous_listen_ts = None

        # Checking if there is a "next" page...
        next_listens = list(db_conn.fetch_listens(user_id, limit=1, to_id=listens[-1]["listened_at"]))
        if next_listens:
            next_listen_ts = listens[-1]["listened_at"]
        else:
            next_listen_ts = None

    else:
        previous_listen_ts = None
        next_listen_ts = None

    return render_template(
        "user/profile.html",
        user=_get_user(user_id),
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
                             user_id=current_user.musicbrainz_id,
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
        db_conn = webserver.create_postgres()
        filename = current_user.musicbrainz_id + "_lb-" + datetime.today().strftime('%Y-%m-%d') + ".json"

        # Fetch output and convert it into dict with keys as indexes
        output = []
        for index, obj in enumerate(db_conn.fetch_listens(current_user.musicbrainz_id)):
            dic = obj.data
            dic['timestamp'] = obj.timestamp
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


@user_bp.route("/upload", methods=['POST'])
@login_required
def upload():
    if request.method == 'POST':
        f = request.files['file']
        if f:
            try:
                jsonlist = json.load(f)
                if not isinstance(jsonlist, list):
                    raise ValueError
            except ValueError:
                raise BadRequest("Not a valid lastfmbackup file.")

            payload = _convert_to_native_format(jsonlist)

            _send_listens_to_redis("import",
                _payload_to_augmented_list(payload, current_user.musicbrainz_id))

            flash('Congratulations !! Your listens have been uploaded successfully.')
    return redirect(url_for("user.import_data"))


def _convert_to_native_format(data):
    """
    Converts the imported listen-payload from the lastfm backup file
    to the native payload format.
    """
    payload = []
    for native_lis in data:
        listen = {}
        listen['track_metadata'] = {}
        listen['track_metadata']['additional_info'] = {}

        if 'timestamp' in native_lis and 'unixtimestamp' in native_lis['timestamp']:
            listen['listened_at'] = native_lis['timestamp']['unixtimestamp']

        if 'track' in native_lis:
            if 'name' in native_lis['track']:
                listen['track_metadata']['track_name'] = native_lis['track']['name']
            if 'mbid' in native_lis['track']:
                listen['track_metadata']['additional_info']['recording_mbid'] = native_lis['track']['mbid']
            if 'artist' in native_lis['track']:
                if 'name' in native_lis['track']['artist']:
                    listen['track_metadata']['artist_name'] = native_lis['track']['artist']['name']
                if 'mbid' in native_lis['track']['artist']:
                    listen['track_metadata']['additional_info']['artist_mbids'] = [native_lis['track']['artist']['mbid']]
        payload.append(listen)
    return payload


def _get_user(user_id):
    """ Get current username """
    if current_user.is_authenticated() and \
       current_user.musicbrainz_id == user_id:
        return current_user
    else:
        user = db.user.get_by_mb_id(user_id)
        if user is None:
            raise NotFound("Can't find this user.")
        return user


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
