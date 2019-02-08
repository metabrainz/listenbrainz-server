import urllib
import ujson
import time
import uuid
from flask import Blueprint, render_template, request, url_for, Response, redirect, flash, current_app, jsonify
from flask_login import current_user
from listenbrainz import webserver
import listenbrainz.db.spotify as db_spotify
from werkzeug.exceptions import NotFound, BadRequest, InternalServerError


follow_bp = Blueprint("follow", __name__)

@follow_bp.route("/", defaults={'user_list': ""})
@follow_bp.route("/<user_list>")
def follow(user_list):
    """ 
        Allow an LB user to follow the stream of one or more other LB users.
    """

    follow_list = []
    for to_follow in user_list.split(","):
        to_follow = to_follow.strip()
        if not to_follow:
            continue
        follow_list.append(to_follow)

    if current_user.is_authenticated:
        user_data = {
            "id"               : current_user.id,
            "name"             : current_user.musicbrainz_id,
            "auth_token"       : current_user.auth_token,
        }
        spotify_access_token = db_spotify.get_token_for_user(current_user.id)
    else:
        user_data = {
            "id"               : 0,
            "name"             : uuid.uuid4().hex,
            "auth_token"       : "",
        }
        spotify_access_token = ""

    props = {
        "user"                 : user_data,
        "mode"                 : "follow",
        "follow_list"          : follow_list,
        "spotify_access_token" : spotify_access_token,
        "web_sockets_server_url": current_app.config['WEBSOCKETS_SERVER_URL'],
    }

    return render_template("user/profile.html", 
        props=ujson.dumps(props),
        mode='follow',
        user=current_user, 
        follow_list=follow_list,
        active_section='listens')
