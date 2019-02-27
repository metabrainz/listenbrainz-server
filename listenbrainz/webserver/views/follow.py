import ujson
import json
from flask import Blueprint, render_template, request, current_app, jsonify
from flask_login import current_user, login_required
from listenbrainz.webserver.login import auth_required
import listenbrainz.db.spotify as db_spotify
import listenbrainz.db.user as db_user
import listenbrainz.db.follow_list as db_follow_list


follow_bp = Blueprint("follow", __name__)

@follow_bp.route("/", defaults={'user_list': ""})
@follow_bp.route("/<user_list>")
@login_required
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

    user_data = {
        "id": current_user.id,
        "name": current_user.musicbrainz_id,
    }
    spotify_access_token = db_spotify.get_token_for_user(current_user.id)
    props = {
        "user": user_data,
        "mode": "follow",
        "follow_list": follow_list,
        "spotify_access_token": spotify_access_token,
        "web_sockets_server_url": current_app.config['WEBSOCKETS_SERVER_URL'],
        "save_url": 'http://0.0.0.0/follow/save',
        'follow_list_name': 'follow-list',
    }

    return render_template(
        "index/follow.html",
        props=ujson.dumps(props),
        mode='follow',
        user=current_user,
        follow_list=follow_list,
        active_section='listens',
    )


@follow_bp.route("/save", methods=["POST"])
@auth_required
def save_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.error(data)
    list_name = data['name']
    users = data['users']
    users = db_user.validate_usernames(users)
    db_follow_list.save(
        name=list_name,
        creator=current_user.id,
        members=[user['id'] for user in users],
    )
