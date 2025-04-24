from datetime import datetime, timezone
import timeago
from math import ceil
from collections import defaultdict

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship

from flask import Blueprint, render_template, request, url_for, jsonify, current_app
from flask_login import current_user, login_required
import psycopg2
from psycopg2.extras import DictCursor

from listenbrainz import webserver
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.db.playlist import get_playlists_for_user, get_recommendation_playlists_for_user, get_playlists_collaborated_on
from listenbrainz.db.pinned_recording import get_current_pin_for_user, get_pin_count_for_user, get_pin_history_for_user
from listenbrainz.db.feedback import get_feedback_count_for_user, get_feedback_for_user
from listenbrainz.db import year_in_music as db_year_in_music
from listenbrainz.db.genre import load_genre_with_subgenres
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver import timescale_connection, db_conn, ts_conn
from listenbrainz.webserver.errors import APIBadRequest
from listenbrainz.webserver.login import User, api_login_required
from listenbrainz.webserver.views.api import DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL
from listenbrainz.webserver.utils import number_readable
from listenbrainz.webserver.views.api_tools import get_non_negative_param

from brainzutils import cache

LISTENS_PER_PAGE = 25
DEFAULT_NUMBER_OF_FEEDBACK_ITEMS_PER_CALL = 25

TAG_HEIRARCHY_CACHE_KEY = "tag_hierarchy"
TAG_HEIRARCHY_CACHE_EXPIRY = 60 * 60 * 24 * 7  # 7 days

user_bp = Blueprint("user", __name__)
redirect_bp = Blueprint("redirect", __name__)


@redirect_bp.route('/', defaults={'path': ''})
@redirect_bp.route('/<path:path>/')
@login_required
def index(path):
    return render_template("index.html", user=current_user)


@user_bp.post("/<user_name>/")
@web_listenstore_needed
def profile(user_name):
    # Which database to use to showing user listens.
    ts_conn = webserver.timescale_connection._ts
    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    # Getting data for current page
    max_ts = request.args.get("max_ts")
    if max_ts is not None:
        try:
            max_ts = int(max_ts)
        except ValueError:
            return jsonify({"error": "Incorrect timestamp argument max_ts: %s" %
                            request.args.get("max_ts")}), 400

    min_ts = request.args.get("min_ts")
    if min_ts is not None:
        try:
            min_ts = int(min_ts)
        except ValueError:
            return jsonify({"error": "Incorrect timestamp argument min_ts: %s" %
                            request.args.get("min_ts")}), 400

    args = {}
    if max_ts:
        args['to_ts'] = datetime.fromtimestamp(max_ts, timezone.utc)
    elif min_ts:
        args['from_ts'] = datetime.fromtimestamp(min_ts, timezone.utc)
    data, min_ts_per_user, max_ts_per_user = ts_conn.fetch_listens(
        user.to_dict(), limit=LISTENS_PER_PAGE, **args)
    min_ts_per_user = int(min_ts_per_user.timestamp())
    max_ts_per_user = int(max_ts_per_user.timestamp())

    listens = []
    for listen in data:
        listens.append(listen.to_api())

    playing_now = playing_now_conn.get_playing_now(user.id)
    if playing_now:
        playing_now = playing_now.to_api()

    already_reported_user = False
    if current_user.is_authenticated:
        already_reported_user = db_user.is_user_reported(db_conn, current_user.id, user.id)

    pin = get_current_pin_for_user(db_conn, user_id=user.id)
    if pin:
        pin = fetch_track_metadata_for_items(webserver.ts_conn, [pin])[0].to_api()

    data = {
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
        "listens": listens,
        "latestListenTs": max_ts_per_user,
        "oldestListenTs": min_ts_per_user,
        "profile_url": url_for('user.index', path="", user_name=user_name),
        "userPinnedRecording": pin,
        "playingNow": playing_now,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
        "already_reported_user": already_reported_user,
    }

    return jsonify(data)


@user_bp.post("/<user_name>/stats/top-artists/")
@user_bp.post("/<user_name>/stats/top-albums/")
@user_bp.post("/<user_name>/stats/top-tracks/")
def charts(user_name):
    """ Show the top entitys for the user. """
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    props = {
        "user": user_data,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(props)


@user_bp.post("/<user_name>/stats/")
def stats(user_name: str):
    """ Show user stats """
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    data = {
        "user": user_data,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(data)


@user_bp.post("/<user_name>/playlists/")
@web_listenstore_needed
def playlists(user_name: str):
    """ Show user playlists """

    page = get_non_negative_param("page", default=1)
    type = request.args.get("type", "")

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    include_private = current_user.is_authenticated and current_user.id == user.id

    playlists = []
    offset = (page - 1) * DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL

    if type == "collaborative":
        user_playlists, playlist_count = get_playlists_collaborated_on(
            db_conn, ts_conn, user.id, include_private=include_private,
            load_recordings=True, count=DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL, offset=offset
        )
    else:
        user_playlists, playlist_count = get_playlists_for_user(
            db_conn, ts_conn, user.id, include_private=include_private,
            load_recordings=True, count=DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL, offset=offset
        )
    for playlist in user_playlists:
        playlists.append(playlist.serialize_jspf())

    data = {
        "playlists": playlists,
        "user": user_data,
        "playlistCount": playlist_count,
        "pageCount": ceil(playlist_count / DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL),
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(data)


@user_bp.post("/<user_name>/recommendations/")
@web_listenstore_needed
def recommendation_playlists(user_name: str):
    """ Show playlists created for user """

    offset = request.args.get('offset', 0)
    try:
        offset = int(offset)
    except ValueError:
        return jsonify({"error": "Incorrect int argument offset: %s" %
                        request.args.get("offset")}), 400

    count = request.args.get("count", DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    try:
        count = int(count)
    except ValueError:
        return jsonify({"error": "Incorrect int argument count: %s" %
                        request.args.get("count")}), 400
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    playlists = []
    user_playlists = get_recommendation_playlists_for_user(db_conn, ts_conn, user.id)
    for playlist in user_playlists:
        playlists.append(playlist.serialize_jspf())

    data = {
        "playlists": playlists,
        "user": user_data,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(data)


@user_bp.post("/<user_name>/report-user/")
@api_login_required
def report_abuse(user_name):
    data = request.json
    reason = None
    if data:
        reason = data.get("reason")
        if not isinstance(reason, str):
            raise APIBadRequest("Reason must be a string.")
    user_to_report = db_user.get_by_mb_id(db_conn, user_name)
    if current_user.id != user_to_report["id"]:
        db_user.report_user(db_conn, current_user.id, user_to_report["id"], reason)
        return jsonify({"status": "%s has been reported successfully." % user_name})
    else:
        raise APIBadRequest("You cannot report yourself.")


def _get_user(user_name):
    """ Get current username """
    if current_user.is_authenticated and \
            current_user.musicbrainz_id == user_name:
        return current_user
    else:
        user = db_user.get_by_mb_id(db_conn, user_name)
        if user is None:
            return None
        return User.from_dbrow(user)


def logged_in_user_follows_user(user):
    """ Check if user is being followed by the current user.
    Args:
        user : User object
    Raises:
        NotFound if user isn't present in the database
    """

    if current_user.is_authenticated:
        return db_user_relationship.is_following_user(
            db_conn, current_user.id, user.id
        )
    return None


@user_bp.post("/<user_name>/taste/")
@web_listenstore_needed
def taste(user_name: str):
    """ Show user feedback(love/hate) and pins.
    Feedback has filter on score (1 or -1).

    Args:
        user_name (str): the MusicBrainz ID of the user
    Raises:
        NotFound if user isn't present in the database
    """

    score = request.args.get('score', 1)
    try:
        score = int(score)
    except ValueError:
        return jsonify({"error": "Incorrect int argument score: %s" %
                        request.args.get("score")}), 400

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    feedback_count = get_feedback_count_for_user(db_conn, user.id, score)
    feedback = get_feedback_for_user(
        db_conn, ts_conn, user_id=user.id, limit=DEFAULT_NUMBER_OF_FEEDBACK_ITEMS_PER_CALL,
        offset=0, score=score, metadata=True
    )
    
    pins = get_pin_history_for_user(db_conn, user_id=user.id, count=25, offset=0)
    pins = [pin.to_api() for pin in fetch_track_metadata_for_items(ts_conn, pins)]
    pin_count = get_pin_count_for_user(db_conn, user_id=user.id)

    data = {
        "feedback": [f.to_api() for f in feedback],
        "feedback_count": feedback_count,
        "user": user_data,
        "active_section": "taste",
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
        "pins": pins,
        "pin_count": pin_count,
        "profile_url": url_for('user.index', path="", user_name=user_name),
    }

    return jsonify(data)


def process_genre_data(yim_top_genre: list, data: list, user_name: str):
    if not yim_top_genre or not data:
        return {}

    yimDataDict = {genre["genre"]: genre["genre_count"] for genre in yim_top_genre}

    adj_matrix = defaultdict(list)
    is_head = defaultdict(lambda: True)
    id_name_map = {}
    parent_map = defaultdict(lambda: None)

    for row in data:
        genre_id = row["genre_gid"]
        is_head[genre_id]
        id_name_map[genre_id] = row.get("genre")

        subgenre_id = row["subgenre_gid"]
        if subgenre_id:
            is_head[subgenre_id] = False
            id_name_map[subgenre_id] = row.get("subgenre")
            parent_map[subgenre_id] = genre_id
            adj_matrix[genre_id].append(subgenre_id)
        else:
            adj_matrix[genre_id] = []

    visited = set()
    rootNodes = [node for node in is_head if is_head[node]]

    def create_node(id):
        if id in visited:
            return None
        visited.add(id)

        genreCount = yimDataDict.get(id_name_map[id], 0)
        children = []

        for subGenre in sorted(adj_matrix[id]):
            childNode = create_node(subGenre)
            if isinstance(childNode, list):
                children.extend(childNode)
            elif childNode is not None:
                children.append(childNode)

        if genreCount == 0:
            if len(children) == 0:
                return None
            return children

        data = {"id": id, "name": id_name_map[id], "children": children, "loc": genreCount}

        if len(children) == 0:
            del data["children"]

        return data

    outputArr = []
    for rootNode in rootNodes:
        node = create_node(rootNode)
        if isinstance(node, list):
            outputArr.extend(node)
        elif node is not None:
            outputArr.append(node)

    return {
        "name": user_name,
        "color": "transparent",
        "children": outputArr
    }


@user_bp.post("/<user_name>/year-in-music/")
@user_bp.post("/<user_name>/year-in-music/<int:year>/")
def year_in_music(user_name, year: int = 2024):
    """ Year in Music """
    if year not in (2021, 2022, 2023, 2024):
        return jsonify({"error": f"Cannot find Year in Music report for year: {year}"}), 404

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    try:
        yearInMusicData = db_year_in_music.get(user.id, year) or {}
    except Exception as e:
        yearInMusicData = {}
        current_app.logger.error(f"Error getting Year in Music data for user {user_name}: {e}")

    genreGraphData = {}
    if yearInMusicData and year == 2024:
        try:
            data = cache.get(TAG_HEIRARCHY_CACHE_KEY)
            if not data:
                with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn,\
                        mb_conn.cursor(cursor_factory=DictCursor) as mb_curs:
                    data = load_genre_with_subgenres(mb_curs)
                    data = [dict(row) for row in data] if data else []
                cache.set(TAG_HEIRARCHY_CACHE_KEY, data, expirein=TAG_HEIRARCHY_CACHE_EXPIRY)
        except Exception as e:
            current_app.logger.error("Error loading genre hierarchy: %s", e)
            return jsonify({"error": "Failed to load genre hierarchy"}), 500

        yimTopGenre = yearInMusicData.get("top_genres", [])
        genreGraphData = process_genre_data(yimTopGenre, data, user_name)

    return jsonify({
        "data": yearInMusicData,
        **({"genreGraphData": genreGraphData} if year == 2024 else {}),
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
    })

# Embedable widgets, return HTML page to embed in an iframe


@user_bp.get("/<user_name>/embed/playing-now/")
def embed_playing_now(user_name):
    """ Returns either the HTML page that load the current playing-now for a user
     or the HTMX fragment consisting only in the playing-now card HTML markup 
     
    The iframe height must be set to 80px, while the width can be adjusted:
    .. code-block:: html

        <iframe
            src="https://listenbrainz.org/user/mr_monkey/embed/playing-now"
            frameborder="0"
            width="650px"
            height="80px"
        ></iframe>
    
    :param user_name: the MusicBrainz ID of the user whose currently playing listen you want to embed.
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *text/html*
    :statuscode 404: The requested user was not found.
    """

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    # If the request has HTMX headers, return partial content for the pin card fragment
    if current_app.htmx:
        return render_playing_now_card(user=user)

    # Otherwise return the container page
    return render_template(
        "widgets/playing_now.html", user_name=user_name
    )


def render_playing_now_card(user):
    """ Returns the HTMX fragment consisting only in the playing-now card HTML markup """

    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis
    playing_now = playing_now_conn.get_playing_now(user.id)

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    if playing_now is None:
        return render_template(
            "widgets/playing_now_card.html",
            user_name=user_name,
            no_playing_now=True
        )

    playing_now = playing_now.to_api()

    metadata = playing_now.get("track_metadata", {})
    mbid_mapping = metadata.get("mbid_mapping", {})
    additional_info = metadata.get("additional_info", {})

    caa_id = mbid_mapping.get("caa_id")
    caa_release_mbid = mbid_mapping.get("caa_release_mbid")
    release_cover_art_src = None
    if caa_id is not None and caa_release_mbid is not None:
        release_cover_art_src = f"https://archive.org/download/mbid-{caa_release_mbid}/mbid-{caa_release_mbid}-{caa_id}_thumb250.jpg"
    release_mbid = (
        additional_info.get("release_mbid")
        or metadata.get("release_mbid")
        or mbid_mapping.get("release_mbid")
    )
    release_name = metadata.get(
        "release_name") or mbid_mapping.get("release_name")

    recording_mbid = (
        additional_info.get("recording_mbid")
        or mbid_mapping.get("recording_mbid")
    )
    recording_name = metadata.get(
        "track_name") or mbid_mapping.get("recording_name")

    artist_mbids_list = mbid_mapping.get("artist_mbids")
    artist_mbid = artist_mbids_list[0] if artist_mbids_list else None
    artist_name = metadata.get("artist_name")

    duration_ms = additional_info.get("duration_ms")
    duration = None
    if duration_ms:
        track_seconds = round(duration_ms / 1000)
        hours, remainder = divmod(track_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            duration = '{:d}:{:02d}:{:02d}'.format(hours, minutes, seconds)
        else:
            duration = '{:d}:{:02d}'.format(minutes, seconds)

    return render_template(
        "widgets/playing_now_card.html",
        user_name=user_name,
        release_cover_art_src=release_cover_art_src,
        release_mbid=release_mbid,
        release_name=release_name,
        recording_mbid=recording_mbid,
        recording_name=recording_name,
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        duration=duration
    )


@user_bp.get("/<user_name>/embed/pin/")
def embed_pin(user_name):
    """ Returns either the HTML page that load the current pin for a user
     or the HTMX fragment consisting only in the pin HTML markup
          
    The iframe height must be set to 150px, while the width can be adjusted:
    .. code-block:: html

        <iframe
            src="https://listenbrainz.org/user/mr_monkey/embed/pin"
            frameborder="0"
            width="650px"
            height="150px"
        ></iframe>
    
    :param user_name: the MusicBrainz ID of the user whose current pin you want to embed.
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *text/html*
    :statuscode 404: The requested user was not found.
    """
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    pin = get_current_pin_for_user(db_conn, user_id=user.id)
    pin_is_current = True

    if pin is None:
        # Fallback to latest pin if no current pin
        pin_is_current = False
        older_pins = get_pin_history_for_user(db_conn, user_id=user.id, count=1, offset=0)
        # If still none, there are no pins to show
        if older_pins is not None and len(older_pins) > 0:
            pin = older_pins[0]

    if pin is None:
        return render_template(
            "widgets/pin_card.html",
            user_name=user_name,
            no_pin=True,
            pin_is_current=False
        )

    pin = fetch_track_metadata_for_items(
        webserver.ts_conn, [pin])[0].to_api()

    metadata = pin.get("track_metadata", {})
    mbid_mapping = metadata.get("mbid_mapping", {})
    additional_info = metadata.get("additional_info", {})

    caa_id = mbid_mapping.get("caa_id")
    caa_release_mbid = mbid_mapping.get("caa_release_mbid")
    release_cover_art_src = None
    if caa_id is not None and caa_release_mbid is not None:
        release_cover_art_src = f"https://archive.org/download/mbid-{caa_release_mbid}/mbid-{caa_release_mbid}-{caa_id}_thumb250.jpg"
    release_mbid = (
        additional_info.get("release_mbid")
        or metadata.get("release_mbid")
        or mbid_mapping.get("release_mbid")
    )
    release_name = metadata.get(
        "release_name") or mbid_mapping.get("release_name")

    recording_mbid = (
        pin.get("recording_mbid")
        or additional_info.get("recording_mbid")
        or mbid_mapping.get("recording_mbid")
    )
    recording_name = metadata.get(
        "track_name") or mbid_mapping.get("recording_name")

    artist_mbids_list = mbid_mapping.get("artist_mbids")
    artist_mbid = artist_mbids_list[0] if artist_mbids_list else None
    artist_name = metadata.get("artist_name")

    pin_date = datetime.fromtimestamp(pin.get("created"))
    pin_date = timeago.format(pin_date)

    duration_ms = additional_info.get("duration_ms")
    duration = None
    if duration_ms:
        track_seconds = round(duration_ms / 1000)
        hours, remainder = divmod(track_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            duration = '{:d}:{:02d}:{:02d}'.format(hours, minutes, seconds)
        else:
            duration = '{:d}:{:02d}'.format(minutes, seconds)

    return render_template(
        "widgets/pin_card.html",
        user_name=user_name,
        release_cover_art_src=release_cover_art_src,
        release_mbid=release_mbid,
        release_name=release_name,
        recording_mbid=recording_mbid,
        recording_name=recording_name,
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        pin_date=pin_date,
        duration=duration,
        pin_is_current=pin_is_current,
        blurb_content=pin.get("blurb_content"),
    )


@user_bp.get("/<user_name>/",  defaults={'path': ''})
@user_bp.get('/<user_name>/<path:path>/')
@web_listenstore_needed
def index(user_name, path):
    user = _get_user(user_name)
    if not user:
        og_meta_tags = None
    else:
        listen_count = None
        try:
            listen_count = timescale_connection._ts.get_listen_count_for_user(user.id)
        except psycopg2.OperationalError as err:
            current_app.logger.error("cannot fetch user listen count: ", str(err))
        og_meta_tags = {
            "title": f"{user_name} on ListenBrainz",
            "description": f'User{f" — {number_readable(listen_count)} listens" if listen_count else ""} — ListenBrainz',
            "type": "profile",
            "profile:username": user_name,
            "url": f'{current_app.config["SERVER_ROOT_URL"]}/user/{user_name}/',
        }
    return render_template("index.html", og_meta_tags=og_meta_tags, user=user)
