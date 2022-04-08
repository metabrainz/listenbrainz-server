from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from werkzeug.exceptions import BadRequest, ServiceUnavailable, NotFound
import ujson

metadata_viewer_bp = Blueprint("metadata_viewer", __name__)

@metadata_viewer_bp.route("/", methods=["GET"])
def playing_now_metadata_viewer():
	
    return render_template(
        "player/metadata-viewer.html",
        # props=ujson.dumps({"playing_now": })
    )