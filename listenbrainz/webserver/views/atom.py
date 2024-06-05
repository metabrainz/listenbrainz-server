from datetime import datetime, timedelta
from feedgen.feed import FeedGenerator
from flask import Blueprint, Response, request
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
    """
    Get listens feed for a user.
    
    :param interval: The time interval in minutes from current time to fetch listens for. For example, if interval=60, listens from the last hour will be fetched. Default is 60.
    :statuscode 200: The feed was successfully generated.
    :statuscode 400: Bad request.
    :statuscode 404: The user does not exist.
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        return Response(status=404)
    
    # Get and validate interval
    interval = request.args.get("interval", 60)
    if interval:
        try:
            interval = int(interval)
        except ValueError:
            return Response(status=400)
    
    if interval < 1:
        return Response(status=400)
    
    # Construct UTC timestamp for interval
    from_ts = datetime.now() - timedelta(minutes=interval)

    listens, _, _ = timescale_connection._ts.fetch_listens(user, from_ts=from_ts)

    fg = FeedGenerator()
    fg.id(f"https://listenbrainz.org/user/{user_name}")
    fg.title(f"Listens for {user_name}")
    fg.author({"name": "ListenBrainz"})
    fg.link(href=f"https://listenbrainz.org/user/{user_name}", rel="alternate")
    fg.link(href=f"https://listenbrainz.org/syndication-feed/user/{user_name}/listens", rel="self")
    fg.logo("https://listenbrainz.org/static/img/listenbrainz_logo_icon.svg")
    fg.language("en")
    
    for listen in listens:
        fe = fg.add_entry()
        # according to spec, ids don't have to be deferencable.
        fe.id(f"https://listenbrainz.org/syndication-feed/user/{user_name}/listens/{listen.ts_since_epoch}/{listen.data['track_name']}")
        fe.title(f"{listen.data['track_name']} - {listen.data['artist_name']}")
        fe.content(f"{listen.user_name} listened to {listen.data['track_name']} - {listen.data['artist_name']} on {listen.timestamp}")
    
    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")
