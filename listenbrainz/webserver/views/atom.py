from feedgen.feed import FeedGenerator
from flask import Blueprint, Response
from listenbrainz.webserver.decorators import crossdomain, api_listenstore_needed
from brainzutils.ratelimit import ratelimit
import listenbrainz.db.user as db_user
from listenbrainz.webserver import db_conn, timescale_connection

atom_bp = Blueprint("atom", __name__)


@atom_bp.route("/user/<user_name>/listens", methods=["GET"])
@crossdomain
@ratelimit()
@api_listenstore_needed
def get_listens(user_name):
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        return Response(status=404)
    
    listens, _, _ = timescale_connection._ts.fetch_listens(user)

    fg = FeedGenerator()
    fg.id(f"https://listenbrainz.org/user/{user_name}")
    fg.title(f"Listens for {user_name}")
    fg.author({"name": "ListenBrainz"})
    fg.link(href=f"https://listenbrainz.org/user/{user_name}", rel="alternate")
    fg.link(href=f"https://listenbrainz.org/feed/user/{user_name}/listens", rel="self")
    fg.logo("https://listenbrainz.org/static/img/listenbrainz_logo_icon.svg")
    fg.language("en")
    
    for listen in listens:
        fe = fg.add_entry()
        fe.id(f"https://listenbrainz.org/user/{user_name}")
        fe.title(f"{listen.user_name} listened to {listen.data['track_name']} - {listen.data['artist_name']} on {listen.timestamp}")
        fe.link(href=f"https://listenbrainz.org/feed/user/{user_name}/listens", rel="self")
    
    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")
