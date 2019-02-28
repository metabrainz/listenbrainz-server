import urllib
import ujson
import time
import uuid
from flask import Blueprint, render_template, request, url_for, Response, redirect, flash, current_app, jsonify
from flask_login import current_user, login_required
from listenbrainz import webserver
import listenbrainz.db.spotify as db_spotify
from werkzeug.exceptions import NotFound, BadRequest, InternalServerError


follow_bp = Blueprint("follow", __name__)


def parse_user_list(users):
    user_list = []
    for user in users.split(","):
        user = user.strip()
        if not user:
            continue
        user_list.append(user)

    return user_list


@follow_bp.route("/", defaults={'user_list': ""})
@follow_bp.route("/<user_list>")
@login_required
def follow(user_list):
    """
        Allow an LB user to follow the stream of one or more other LB users.
    """

    follow_list = parse_user_list(user_list)
    user_data = {
        "id"               : current_user.id,
        "name"             : current_user.musicbrainz_id,
    }
    spotify_access_token = db_spotify.get_token_for_user(current_user.id)
    props = {
        "user"                 : user_data,
        "mode"                 : "follow",
        "follow_list"          : follow_list,
        "spotify_access_token" : spotify_access_token,
        "web_sockets_server_url": current_app.config['WEBSOCKETS_SERVER_URL'],
    }

    return render_template("index/follow.html",
        props=ujson.dumps(props),
        mode='follow',
        user=current_user,
        follow_list=follow_list,
        active_section='listens')
