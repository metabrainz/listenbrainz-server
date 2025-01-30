from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, current_app

from listenbrainz.db.donation import get_recent_donors, get_biggest_donors, are_users_eligible_donors
from listenbrainz.db.user_setting import get_all_flairs
from listenbrainz.webserver import db_conn, meb_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.views.api_tools import _parse_int_arg

donor_api_bp = Blueprint('donor_api_v1', __name__)


DEFAULT_DONOR_COUNT = 25


@donor_api_bp.get("/recent")
@crossdomain
@ratelimit()
def recent_donors():
    """ Get a list of most recent MeB donors with flairs.

    """
    count = _parse_int_arg("count", DEFAULT_DONOR_COUNT)
    offset = _parse_int_arg("offset", 0)

    if not current_app.config["SQLALCHEMY_METABRAINZ_URI"]:
        return []

    donors, _ = get_recent_donors(meb_conn, db_conn, count, offset)
    return jsonify(donors)


@donor_api_bp.get("/biggest")
@crossdomain
@ratelimit()
def biggest_donors():
    """ Get a list of the biggest MeB donors with flairs.

    """
    count = _parse_int_arg("count", DEFAULT_DONOR_COUNT)
    offset = _parse_int_arg("offset", 0)

    if not current_app.config["SQLALCHEMY_METABRAINZ_URI"]:
        return []

    donors, _ = get_biggest_donors(meb_conn, db_conn, count, offset)
    return jsonify(donors)


@donor_api_bp.get("/all-flairs")
@crossdomain
@ratelimit()
def all_flairs():
    """ Get flairs for all eligible users.

        Returns a JSON object with username as key and the flair description as value. Example:

        .. code:: json

            {
                "rob": {
                    "color": "orange"
                },
                "lucifer": {
                    "emoji": "devil"
                }
            }
    """
    users_with_flair = get_all_flairs(db_conn)
    eligible_donors = are_users_eligible_donors(meb_conn, [u.musicbrainz_row_id for u in users_with_flair])

    result = {
        r.musicbrainz_id: r.flair
        for r in users_with_flair
        if r.musicbrainz_row_id in eligible_donors and eligible_donors[r.musicbrainz_row_id]
    }
    return jsonify(result)
