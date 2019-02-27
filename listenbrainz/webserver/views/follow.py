import ujson
import json
from flask import Blueprint, render_template, request, current_app, jsonify
from flask_login import current_user, login_required
from listenbrainz.webserver.login import auth_required
import listenbrainz.db.spotify as db_spotify
import listenbrainz.db.user as db_user
import listenbrainz.db.follow_list as db_follow_list


follow_bp = Blueprint("follow", __name__)

@follow_bp.route("/", defaults={"user_list": ""})
@follow_bp.route("/<user_list>")
@login_required
def follow(user_list):
    """ Allow an LB user to follow the stream of one or more other LB users.
    """
    if user_list:
        default_list = {'name': 'Untitled Follow List'}
        follow_list_members = [member.strip() for member in user_list.split(",") if member.strip()]
    else:
        default_list = db_follow_list.get_latest(creator=current_user.id)
        if not default_list:
            default_list = {'name': 'Untitled Follow List', 'members': []}
        follow_list_members = [member['musicbrainz_id'] for member in default_list['members']]

    user_data = {
        "id": current_user.id,
        "name": current_user.musicbrainz_id,
    }
    spotify_access_token = db_spotify.get_token_for_user(current_user.id)
    props = {
        "user": user_data,
        "mode": "follow",
        "follow_list": follow_list_members,
        "spotify_access_token": spotify_access_token,
        "web_sockets_server_url": current_app.config["WEBSOCKETS_SERVER_URL"],
        "save_url": "http://0.0.0.0/follow/save", #TODO
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


@follow_bp.route("/save", methods=["POST"])
@auth_required
def save_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.error(data)
    list_name = data['name']
    users = data['users']
    users = db_user.validate_usernames(users)
    try:
        list_id = db_follow_list.save(
            name=list_name,
            creator=current_user.id,
            members=[user['id'] for user in users],
        )
    except Exception as e:
        current_app.logger.error(str(e))
    return jsonify({
        "code": 200,
        "message": "it worked!",
        "list_id": list_id,
    })
