import locale
import os
import time
from datetime import datetime
from typing import List

from brainzutils import cache
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, current_app, request, jsonify
from flask_login import current_user, login_required
from requests.exceptions import HTTPError
from werkzeug.exceptions import Unauthorized, NotFound

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
from data.model.user_entity import EntityRecord
from listenbrainz.background.background_tasks import add_task
from listenbrainz.db.donation import get_recent_donors
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.db.pinned_recording import get_current_pin_for_users
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.webserver import flash, db_conn, meb_conn, ts_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.redis_connection import _redis
from listenbrainz.webserver.timescale_connection import _ts
from listenbrainz.webserver.views.status_api import get_service_status
from listenbrainz.webserver.views.user_timeline_event_api import get_feed_events_for_user

index_bp = Blueprint('index', __name__)
locale.setlocale(locale.LC_ALL, '')

STATS_PREFIX = 'listenbrainz.stats'  # prefix used in key to cache stats
CACHE_TIME = 10 * 60  # time in seconds we cache the stats
NUMBER_OF_RECENT_LISTENS = 50

SEARCH_USER_LIMIT = 100  # max number of users to return in search username results


@index_bp.post("/")
def index():
    if _ts:
        try:
            listen_count = _ts.get_total_listen_count()
        except Exception as e:
            current_app.logger.error('Error while trying to get total listen count: %s', str(e))
            listen_count = 0
    else:
        listen_count = 0

    artist_count = 0
    try:
        artist_stats = db_stats.get(db_stats.SITEWIDE_STATS_USER_ID, "artists", "all_time", EntityRecord)
        if artist_stats is not None:
            artist_count = artist_stats.count
    except Exception as e:
        current_app.logger.error('Error while trying to get total artist count: %s', str(e))

    props = {
        "listenCount": listen_count,
        "artistCount": artist_count,
    }

    return jsonify(props)


@index_bp.post("/current-status/")
@web_listenstore_needed
def current_status():
    load = "%.2f %.2f %.2f" % os.getloadavg()

    service_status = get_service_status()
    listen_count = _ts.get_total_listen_count()
    try:
        user_count = format(int(_get_user_count()), ',d')
    except DatabaseException as e:
        user_count = 'Unknown'

    listen_counts_per_day: List[dict] = []
    for delta in range(2):
        try:
            day = datetime.utcnow() - relativedelta(days=delta)
            day_listen_count = _redis.get_listen_count_for_day(day)
        except:
            current_app.logger.error("Could not get %s listen count from redis", day.strftime('%Y-%m-%d'),
                                     exc_info=True)
            day_listen_count = None
        listen_counts_per_day.append({
            "date": day.strftime('%Y-%m-%d'),
            "listenCount": format(day_listen_count, ',d') if day_listen_count else "0",
            "label": "today" if delta == 0 else "yesterday",
        })

    data = {
        "load": load,
        "service-status": service_status,
        "listenCount": format(int(listen_count), ",d") if listen_count else "0",
        "userCount": user_count,
        "listenCountsPerDay": listen_counts_per_day,
    }

    return jsonify(data)


@index_bp.post("/recent/")
def recent_listens():
    recent = []
    for listen in _redis.get_recent_listens(NUMBER_OF_RECENT_LISTENS):
        recent.append({
            "track_metadata": listen.data,
            "user_name": listen.user_name,
            "listened_at": listen.ts_since_epoch,
            "listened_at_iso": listen.timestamp.isoformat() + "Z",
        })

    listen_count = _ts.get_total_listen_count()
    try:
        user_count = format(int(_get_user_count()), ',d')
    except DatabaseException as e:
        user_count = 'Unknown'

    # Get recent donors in production environment only.
    if current_app.config["SQLALCHEMY_METABRAINZ_URI"]:
        recent_donors, _ = get_recent_donors(meb_conn, db_conn, 25, 0)
    else:
        recent_donors = []

    # Get MusicBrainz IDs for donors who are ListenBrainz users
    musicbrainz_ids = [donor["musicbrainz_id"]
                       for donor in recent_donors
                       if donor.get('is_listenbrainz_user')]

    # Fetch donor info only if there are valid MusicBrainz IDs
    donors_info = db_user.get_many_users_by_mb_id(db_conn, musicbrainz_ids) if musicbrainz_ids else {}
    donor_ids = [donor_info.id for donor_info in donors_info.values()]

    # Get current pinned recordings
    pinned_recordings_data = {}
    if donor_ids:
        pinned_recordings = get_current_pin_for_users(db_conn, donor_ids)
        if pinned_recordings:
            pinned_recordings_metadata = fetch_track_metadata_for_items(ts_conn, pinned_recordings)
            # Map recordings by user_id for quick lookup
            pinned_recordings_data = {recording.user_id: dict(recording)
                                      for recording in pinned_recordings_metadata}

    # Add pinned recordings to recent donors
    for donor in recent_donors:
        donor_info = donors_info.get(donor["musicbrainz_id"])
        donor["pinnedRecording"] = pinned_recordings_data.get(donor_info.id) if donor_info else None

    props = {
        "listens": recent,
        "globalListenCount": listen_count,
        "globalUserCount": user_count,
        "recentDonors": recent_donors,
    }

    return jsonify(props)


@index_bp.route('/agree-to-terms/', methods=['GET', 'POST'])
@login_required
def gdpr_notice():
    if request.method == 'GET':
        return render_template('index.html')
    elif request.method == 'POST':
        if request.form.get('gdpr-options') == 'agree':
            try:
                db_user.agree_to_gdpr(db_conn, current_user.musicbrainz_id)
            except DatabaseException as e:
                flash.error('Could not store agreement to GDPR terms')
            return jsonify({'status': 'agreed'})
        else:
            return jsonify({'status': 'not_agreed'}), 400


@index_bp.post("/search/")
def search():
    search_term = request.args.get("search_term")
    user_id = current_user.id if current_user.is_authenticated else None
    if search_term:
        users = db_user.search(db_conn, search_term, SEARCH_USER_LIMIT, user_id)
    else:
        users = []

    return jsonify({
        "searchTerm": search_term,
        "users": users
    })


@index_bp.post("/feed/")
@login_required
def feed():
    user_id = current_user.id
    count = request.args.get('count', 25)
    min_ts = request.args.get('min_ts', 0)
    max_ts = request.args.get('max_ts', int(time.time()))
    current_user_data = {
        "id": current_user.id,
        "musicbrainz_id": current_user.musicbrainz_id,
    }

    users_following = db_user_relationship.get_following_for_user(
        db_conn, user_id)

    user_events = get_feed_events_for_user(
        user=current_user_data, followed_users=users_following, min_ts=min_ts, max_ts=max_ts, count=count)

    user_events = user_events[:count]

    # Sadly, we need to serialize the event_type ourselves, otherwise, jsonify converts it badly.
    for index, event in enumerate(user_events):
        user_events[index].event_type = event.event_type.value

    return jsonify({
        'events': [event.dict() for event in user_events],
    })


@index_bp.get("/delete-user/<int:musicbrainz_row_id>")
def mb_user_deleter(musicbrainz_row_id):
    """ This endpoint is used by MusicBrainz to delete accounts once they
    are deleted on MusicBrainz too.

    See https://tickets.metabrainz.org/browse/MBS-9680 for details.

    Args: musicbrainz_row_id (int): the MusicBrainz row ID of the user to be deleted.

    Returns: 200 if the user has been successfully found and deleted from LB

    Raises:
        NotFound if the user is not found in the LB database
        Unauthorized if the MusicBrainz access token provided with the query is invalid
    """
    _authorize_mb_user_deleter(request.args.get('access_token', ''))
    user = db_user.get_by_mb_row_id(db_conn, musicbrainz_row_id)
    if user is None:
        raise NotFound('Could not find user with MusicBrainz Row ID: %d' % musicbrainz_row_id)
    add_task(user['id'], 'delete_user')
    return jsonify({'status': 'ok'}), 200


def _authorize_mb_user_deleter(auth_token):
    try:
        service = MusicBrainzService()
        data = service.get_user_info(auth_token)
    except HTTPError:
        raise Unauthorized('Not authorized to use this view')

    try:
        # 2007538 is the row ID of the `UserDeleter` account that is
        # authorized to access the `delete-user` endpoint
        if data['sub'] != 'UserDeleter' or data['metabrainz_user_id'] != 2007538:
            raise Unauthorized('Not authorized to use this view')
    except KeyError:
        raise Unauthorized('Not authorized to use this view')


def _get_user_count():
    """ Gets user count from either the brainzutils cache or from the database.
        If not present in the cache, it makes a query to the db and stores the
        result in the cache for 10 minutes.
    """
    user_count_key = "{}.{}".format(STATS_PREFIX, 'user_count')
    user_count = cache.get(user_count_key, decode=False)
    if user_count:
        return user_count
    else:
        user_count = db_user.get_user_count(db_conn)
        cache.set(user_count_key, int(user_count), CACHE_TIME, encode=False)
        return user_count


@index_bp.get("/", defaults={'path': ''})
@index_bp.get('/<not_api_path:path>/')
@web_listenstore_needed
def index_pages(path):
    # this is a catch-all route, all unmatched urls match this route instead of raising a 404
    # at least in the case the of API urls, we don't want this behavior. hence detect api urls
    # in the custom NotApiConverter and raise 404 errors manually
    return render_template("index.html")
