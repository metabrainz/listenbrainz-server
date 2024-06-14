from datetime import datetime, timedelta, date, timezone
from feedgen.feed import FeedGenerator
from flask import Blueprint, Response, current_app, jsonify, request
import listenbrainz
from listenbrainz.webserver.decorators import crossdomain, api_listenstore_needed
from brainzutils.ratelimit import ratelimit
import listenbrainz.db.user as db_user
from listenbrainz.webserver import db_conn, timescale_connection
from listenbrainz.webserver.views.api_tools import _parse_bool_arg, _parse_int_arg
from listenbrainz.webserver.views.explore_api import (
    DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS,
    MAX_NUMBER_OF_FRESH_RELEASE_DAYS,
)
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.db.fresh_releases import get_sitewide_fresh_releases

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
    # TODO: use {base_url} instead of hardcoded url
    fg.id(f"https://listenbrainz.org/user/{user_name}")
    fg.title(f"Listens for {user_name}")
    fg.author({"name": "ListenBrainz"})
    fg.link(href=f"https://listenbrainz.org/user/{user_name}", rel="alternate")
    fg.link(
        href=f"https://listenbrainz.org/syndication-feed/user/{user_name}/listens",
        rel="self",
    )
    fg.logo("https://listenbrainz.org/static/img/listenbrainz_logo_icon.svg")
    fg.language("en")

    # newer listen comes first
    for listen in reversed(listens):
        fe = fg.add_entry()
        # according to spec, ids don't have to be deferencable.
        fe.id(
            f"https://listenbrainz.org/syndication-feed/user/{user_name}/listens/{listen.ts_since_epoch}/{listen.data['track_name']}"
        )
        fe.title(f"{listen.data['track_name']} - {listen.data['artist_name']}")

        release_mbid = listen.data["additional_info"].get("release_mbid")
        recording_mbid = listen.data["additional_info"].get("recording_mbid")
        submission_client = listen.data["additional_info"].get("submission_client")

        fe.content(
            content=f"""<p>{listen.user_name} listened to {listen.data['track_name']} - {listen.data['artist_name']} on {listen.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
{"<p>Release: <a href='https://musicbrainz.org/release/" + release_mbid + "'>" + release_mbid + "</a></p>" if release_mbid else ""}
{"<p>Recording: <a href='https://musicbrainz.org/recording/" + recording_mbid + "'>" + recording_mbid + "</a></p>" if recording_mbid else ""}
{"<p>Submission client: " + submission_client + "</p>" if submission_client else ""}
""",
            type="html",
        )

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.route("/fresh_releases", methods=["GET"])
@crossdomain
@ratelimit()
def get_fresh_releases():
    """
    Get site-wide fresh releases.

    :param days: The number of days of fresh releases to show. Max 90 days.
    :param past: Whether to show releases in the past. Default True.
    :param future: Whether to show releases in the future. Default True.
    :statuscode 200: The feed was successfully generated.
    :statuscode 400: Bad request.
    :statuscode 500: Server failed to get latest release.
    :resheader Content-Type: *application/atom+xml*
    """
    days = _parse_int_arg("days", DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS)
    if days < 1 or days > MAX_NUMBER_OF_FRESH_RELEASE_DAYS:
        return Response(status=400)

    past = _parse_bool_arg("past", True)
    future = _parse_bool_arg("future", True)

    try:
        db_releases, total_count = get_sitewide_fresh_releases(
            ts_conn, date.today(), days, "release_date", past, future
        )
    except Exception as e:
        current_app.logger.error("Server failed to get latest release: {}".format(e))
        raise Response(status=500)

    fg = FeedGenerator()
    fg.id(f"https://listenbrainz.org/explore/fresh-releases")
    fg.title(f"Fresh Releases")
    fg.author({"name": "ListenBrainz"})
    fg.link(href=f"https://listenbrainz.org/explore/fresh-releases", rel="alternate")
    fg.link(
        href=f"https://listenbrainz.org/syndication-feed/fresh_releases",
        rel="self",
    )
    fg.logo("https://listenbrainz.org/static/img/listenbrainz_logo_icon.svg")
    fg.language("en")

    # newer listen comes first
    for r in db_releases:
        fe = fg.add_entry()
        # according to spec, ids don't have to be deferencable.
        fe.id(
            f"https://listenbrainz.org/syndication-feed/fresh_releases/{r.release_date.strftime('%Y-%m-%d')}/{r.artist_credit_name}/{r.release_name}"
        )
        fe.title(
            f"{r.release_name} - {r.artist_credit_name} on {r.release_date.strftime('%Y-%m-%d')}"
        )
        fe.content(
            content=f"""<p>{r.artist_credit_name} released {r.release_name} on {r.release_date.strftime('%Y-%m-%d')}</p>""",
            type="html",
        )
        fe.updated(datetime.now(timezone.utc))

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")
