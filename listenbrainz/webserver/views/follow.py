import ujson
from flask import Blueprint, render_template, current_app
from flask_login import current_user, login_required
from listenbrainz.domain import spotify

import listenbrainz.db.follow_list as db_follow_list


follow_bp = Blueprint("follow", __name__)

def parse_user_list(users):
    user_list = []
    for user in users.split(","):
        user = user.strip()
        if not user:
            continue
        user_list.append(user)

    return user_list


@follow_bp.route("/", defaults={"user_list": ""})
@follow_bp.route("/<user_list>")
@login_required
def follow(user_list):
    """ Allow an LB user to follow the stream of one or more other LB users.
    """

    if user_list:
        default_list = {'name': ''}
        follow_list_members = parse_user_list(user_list)
    else:
        default_list = db_follow_list.get_latest(creator=current_user.id)
        if not default_list:
            default_list = {'name': '', 'members': []}
        follow_list_members = [member['musicbrainz_id'] for member in default_list['members']]

    user_data = {
        "id": current_user.id,
        "name": current_user.musicbrainz_id,
        "auth_token": current_user.auth_token,
    }
    spotify_data = spotify.get_user_dict(current_user.id)
    props = {
        "user": user_data,
        "mode": "follow",
        "follow_list": follow_list_members,
        "spotify": spotify_data,
        "web_sockets_server_url": current_app.config["WEBSOCKETS_SERVER_URL"],
        "api_url": current_app.config["API_URL"],
        "save_url": "{}/1/follow/save".format(current_app.config["API_URL"]),
        "follow_list_name": default_list["name"],
        "follow_list_id": default_list["id"] if "id" in default_list else None,
    }

    return render_template(
        "index/follow.html",
        props=ujson.dumps(props),
        mode='follow',
        user=current_user,
        follow_list=follow_list_members,
        active_section='listens',
    )
