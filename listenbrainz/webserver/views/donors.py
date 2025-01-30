from flask import Blueprint, render_template, jsonify, request
from math import ceil

from listenbrainz.webserver.views.api_tools import _parse_int_arg

from listenbrainz.db.donation import get_recent_donors, get_biggest_donors
from listenbrainz.webserver import db_conn, meb_conn, ts_conn, timescale_connection
import listenbrainz.db.user as db_user
import listenbrainz.db.playlist as db_playlist

DEFAULT_DONOR_COUNT = 25
donors_bp = Blueprint("donors", __name__)


@donors_bp.get("/",  defaults={'path': ''})
@donors_bp.get('/<path:path>/')
def donors(path):
    return render_template("index.html")


@donors_bp.post("/")
def donors_post():
    page = _parse_int_arg("page", 1)
    sort = request.args.get("sort", "date")
    offset = (int(page) - 1) * DEFAULT_DONOR_COUNT

    if sort == "amount":
        donors, donation_count = get_biggest_donors(meb_conn, db_conn, DEFAULT_DONOR_COUNT, offset)
    else:
        donors, donation_count = get_recent_donors(meb_conn, db_conn, DEFAULT_DONOR_COUNT, offset)

    donation_count_pages = ceil(donation_count / DEFAULT_DONOR_COUNT)

    musicbrainz_ids = [donor["musicbrainz_id"] for donor in donors if donor['is_listenbrainz_user']]
    donors_info = db_user.get_many_users_by_mb_id(db_conn, musicbrainz_ids) if musicbrainz_ids else {}
    donor_ids = [donor_info.id for _, donor_info in donors_info.items()]

    user_listen_count = timescale_connection._ts.get_listen_count_for_users(donor_ids) if donor_ids else {}
    user_playlist_count = db_playlist.get_playlist_count(ts_conn, donor_ids) if donor_ids else {}

    for donor in donors:
        donor_info = donors_info.get(donor["musicbrainz_id"].lower())
        if not donor_info:
            donor['listenCount'] = None
            donor['playlistCount'] = None
        else:
            donor['listenCount'] = user_listen_count.get(donor_info.id, 0)
            donor['playlistCount'] = user_playlist_count.get(donor_info.id, 0)

    return jsonify({
        "data": donors,
        "totalPageCount": donation_count_pages,
    })
