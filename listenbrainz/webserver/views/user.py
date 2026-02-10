from datetime import datetime
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
from listenbrainz.db.genre import get_tag_hierarchy_data
from listenbrainz.db.year_in_music import LAST_FM_FOUNDING_YEAR, MAX_YEAR_IN_MUSIC_YEAR
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver import timescale_connection, db_conn, ts_conn
from listenbrainz.webserver.errors import APIBadRequest
from listenbrainz.webserver.login import User, api_login_required
from listenbrainz.webserver.views.api import DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL
from listenbrainz.webserver.utils import number_readable
from listenbrainz.webserver.views.api_tools import get_non_negative_param, _parse_datetime_arg, _parse_bool_arg, _parse_int_arg

from brainzutils import cache

LISTENS_PER_PAGE = 25
DEFAULT_NUMBER_OF_FEEDBACK_ITEMS_PER_CALL = 25

user_bp = Blueprint("user", __name__)
redirect_bp = Blueprint("redirect", __name__)


@redirect_bp.route('/', defaults={'path': ''})
@redirect_bp.route('/<path:path>/')
@login_required
def index(path):
    return render_template("index.html", user=current_user)


@user_bp.post("/<mb_username:user_name>/")
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
    args = {"limit": LISTENS_PER_PAGE}
    if max_ts := _parse_datetime_arg("max_ts"):
        args["to_ts"] = max_ts
    elif min_ts := _parse_datetime_arg("min_ts"):
        args["from_ts"] = min_ts
    data = ts_conn.fetch_listens_with_cache(
        user.to_dict(), **args
    )

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
        "listens": data["listens"],
        "latestListenTs": data["latest_listen_ts"],
        "oldestListenTs": data["oldest_listen_ts"],
        "profile_url": url_for("user.index", path="", user_name=user_name),
        "userPinnedRecording": pin,
        "playingNow": playing_now,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
        "already_reported_user": already_reported_user,
    }

    return jsonify(data)


@user_bp.post("/<mb_username:user_name>/stats/top-artists/")
@user_bp.post("/<mb_username:user_name>/stats/top-albums/")
@user_bp.post("/<mb_username:user_name>/stats/top-tracks/")
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


@user_bp.post("/<mb_username:user_name>/stats/")
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


@user_bp.post("/<mb_username:user_name>/playlists/")
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


@user_bp.post("/<mb_username:user_name>/recommendations/")
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


@user_bp.post("/<mb_username:user_name>/report-user/")
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


@user_bp.post("/<mb_username:user_name>/taste/")
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


@user_bp.post("/<mb_username:user_name>/year-in-music/legacy/<int:year>/")
def legacy_year_in_music(user_name, year: int):
    """ Year in Music """
    if year not in (2021, 2022, 2023, 2024):
        return jsonify({"error": f"Cannot find legacy Year in Music report for year: {year}"}), 404

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    try:
        year_in_music_data = db_year_in_music.get(user.id, year, legacy=True) or {}
    except Exception as e:
        year_in_music_data = {}
        current_app.logger.error(f"Error getting Year in Music data for user {user_name}: {e}")

    response = {
        "data": year_in_music_data,
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        }
    }

    if year_in_music_data and year == 2024:
        try:
            data = get_tag_hierarchy_data()
        except Exception as e:
            current_app.logger.error("Error loading genre hierarchy: %s", e)
            return jsonify({"error": "Failed to load genre hierarchy"}), 500

        yim_top_genres = year_in_music_data.get("top_genres", [])
        genre_graph_data = db_year_in_music.process_genre_data(yim_top_genres, data, user_name)
        response["genreGraphData"] = genre_graph_data
    else:
        response["genreGraphData"] = {}

    return jsonify(response)


@user_bp.get("/<mb_username:user_name>/year-in-music/<int:year>/")
def year_in_music_get(user_name, year: int):
    """ Get Year in Music data for a user """
    user = _get_user(user_name)
    if not user:
        og_meta_tags = None
    else:
        current_app.config['SERVER_ROOT_URL'] = "https://test.listenbrainz.org"
        url = f'{current_app.config["SERVER_ROOT_URL"]}/user/{user_name}/year-in-music/{year}/'
        title = f"ListenBrainz {year} Year in Music for {user_name}"
        description = f'Check out the music review for {year} that @ListenBrainz created from my listening history!'
        image = f"{current_app.config['SERVER_ROOT_URL']}/static/img/explore/year-in-music.png"

        og_meta_tags = {
            "title": title,
            "description": description,
            "url": url,
            "image": image,
            "image:type": "image/png",
        }

    return render_template("index.html", og_meta_tags=og_meta_tags, user=user)

@user_bp.post("/<mb_username:user_name>/year-in-music/<int:year>/")
def year_in_music(user_name, year: int):
    """ Year in Music """
    if year < LAST_FM_FOUNDING_YEAR or year > MAX_YEAR_IN_MUSIC_YEAR:
        return jsonify({"error": f"Cannot find Year in Music report for year: {year}"}), 404

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    try:
        year_in_music_data = db_year_in_music.get(user.id, year) or {}
    except Exception as e:
        year_in_music_data = {}
        current_app.logger.error(f"Error getting Year in Music data for user {user_name}: {e}")

    response = {
        "data": year_in_music_data,
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        }
    }

    try:
        data = get_tag_hierarchy_data()
    except Exception as e:
        current_app.logger.error("Error loading genre hierarchy: %s", e)
        return jsonify({"error": "Failed to load genre hierarchy"}), 500

    yim_top_genres = year_in_music_data.get("top_genres", [])
    genre_graph_data = db_year_in_music.process_genre_data(yim_top_genres, data, user_name)
    response["genreGraphData"] = genre_graph_data

    return jsonify(response)


@user_bp.post("/<mb_username:user_name>/year-in-music/")
def year_in_music_covers(user_name):
    """ Get Year in Music cover "cover art" data for all years for a user.

    Returns a list of objects containing year, caa_id, and caa_release_mbid
    for the user's topmost album that has cover art for that year.
    """
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    covers = db_year_in_music.get_yim_covers_for_user(user.id)

    return jsonify({
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
        "data": covers,
    })


# Embedable widgets, return HTML page to embed in an iframe


@user_bp.get("/<mb_username:user_name>/embed/playing-now/")
def embed_playing_now(user_name):
    """ Returns either the HTML page that load the current playing-now for a user
     or the HTMX fragment consisting only in the playing-now card HTML markup 
     
    The iframe height must be set to 80px, while the width can be adjusted:
    .. code-block:: html

        <iframe
            src="https://listenbrainz.org/user/mr_monkey/embed/playing-now"
            frameborder="0"
            width="650"
            height="80"
        ></iframe>
    
    :param user_name: the MusicBrainz ID of the user whose currently playing listen you want to embed.
    :param include_last_listen: Show last listen if not currently playing. Default: ``False``
    :param refresh_interval: Auto-refresh interval in minutes (1-60). Default: ``1``
    :param width: Custom width in pixels. Default: ``650``
    :param height: Custom height in pixels. Default: ``80``
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *text/html*
    :statuscode 404: The requested user was not found.
    """

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    include_last_listen = _parse_bool_arg('include_last_listen', default=False)
    refresh_interval = _parse_int_arg('refresh_interval', default=1)
    if refresh_interval < 1 or refresh_interval > 60:
        refresh_interval = 1
    width = _parse_int_arg('width', default=650)
    height = _parse_int_arg('height', default=80)

    # HTMX request - return just the card fragment
    if current_app.htmx:
        return render_playing_now_card(user=user, include_last_listen=include_last_listen)

    return render_template(
        "widgets/playing_now.html", 
        user_name=user_name,
        refresh_interval=refresh_interval,
        width=width,
        height=height
    )


def render_playing_now_card(user, include_last_listen=False):
    """ Returns the HTMX fragment consisting only in the playing-now card HTML markup """

    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis
    playing_now = playing_now_conn.get_playing_now(user.id)

    # Track if we have actual playing_now data (before potentially using last_listen)
    is_playing_now = playing_now is not None

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    # If no playing_now and include_last_listen is enabled, fetch the last listen
    if playing_now is None and include_last_listen:
        ts_conn = webserver.timescale_connection._ts
        try:
            listens_data = ts_conn.fetch_listens(user.to_dict(), from_ts=None, to_ts=None, limit=1)
            if listens_data and len(listens_data) > 0:
                playing_now = listens_data[0]
        except Exception:
            # If fetching fails, just don't show last listen
            pass

    if playing_now is None:
        return render_template(
            "widgets/playing_now_card.html",
            user_name=user_name,
            no_playing_now=True
        )

    # Use playing_now data
    listen_data = playing_now.to_api()

    metadata = listen_data.get("track_metadata", {})
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

    listened_at = listen_data.get("listened_at")
    listen_date = None
    if listened_at:
        listen_date = datetime.fromtimestamp(listened_at)
        listen_date = timeago.format(listen_date)

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
        duration=duration,
        is_playing_now=is_playing_now,
        listen_date=listen_date
    )


@user_bp.get("/<mb_username:user_name>/embed/pin/")
def embed_pin(user_name):
    """ Returns either the HTML page that load the current pin for a user
     or the HTMX fragment consisting only in the pin HTML markup
          
    The iframe height must be set to 150px, while the width can be adjusted:
    .. code-block:: html

        <iframe
            src="https://listenbrainz.org/user/mr_monkey/embed/pin"
            frameborder="0"
            width="650"
            height="155"
        ></iframe>
    
    :param user_name: the MusicBrainz ID of the user whose current pin you want to embed.
    :param include_last_pin: Show last pin if no active pin. Default: ``True``
    :param include_blurb: Show pin text blurb. Default: ``True``
    :param width: Custom width in pixels. Default: ``650``
    :param height: Custom height in pixels. Default: ``155``
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *text/html*
    :statuscode 404: The requested user was not found.
    """
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    include_last_pin = _parse_bool_arg('include_last_pin', default=True)
    include_blurb = _parse_bool_arg('include_blurb', default=True)
    width = _parse_int_arg('width', default=650)
    height = _parse_int_arg('height', default=155)

    pin = get_current_pin_for_user(db_conn, user_id=user.id)
    pin_is_current = True

    if pin is None and include_last_pin:
        pin_is_current = False
        older_pins = get_pin_history_for_user(db_conn, user_id=user.id, count=1, offset=0)
        if older_pins and len(older_pins) > 0:
            pin = older_pins[0]

    if pin is None:
        return render_template(
            "widgets/pin_card.html",
            user_name=user_name,
            no_pin=True,
            pin_is_current=False,
            width=width,
            height=height
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
        blurb_content=pin.get("blurb_content") if include_blurb else None,
        width=width,
        height=height
    )


@user_bp.get("/<mb_username:user_name>/",  defaults={'path': ''})
@user_bp.get('/<mb_username:user_name>/<path:path>/')
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
