from flask import Blueprint, jsonify

import listenbrainz.db.user as db_user
from listenbrainz.db.release_radar import get_release_radar_data
from listenbrainz.webserver.errors import APINoContent

release_radar_bp = Blueprint('release_radar_v1', __name__)


@release_radar_bp.route("/user/<user_name>/release_radar")
def get_releases(user_name):
    """ Get release radar data for the given user. """
    user = db_user.get_by_mb_id(user_name)
    data = get_release_radar_data(user["id"])

    if data is None:
        raise APINoContent('')

    return jsonify({"payload": data})
