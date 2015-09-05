from __future__ import absolute_import
from flask import Blueprint, render_template
from flask_login import current_user
from werkzeug.exceptions import NotFound
import db.user
import db.dataset

user_bp = Blueprint("user", __name__)


@user_bp.route("/<musicbrainz_id>")
def profile(musicbrainz_id):
    if current_user.is_authenticated() and \
       current_user.musicbrainz_id == musicbrainz_id:
        user = current_user
        datasets = db.dataset.get_by_user_id(user.id, public_only=False)
    else:
        user = db.user.get_by_mb_id(musicbrainz_id)
        if user is None:
            raise NotFound("Can't find this user.")
        datasets = db.dataset.get_by_user_id(user["id"])

    return render_template("user/profile.html", user=user, datasets=datasets)
