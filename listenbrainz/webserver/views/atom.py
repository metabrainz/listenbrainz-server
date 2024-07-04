from datetime import datetime, timedelta, date, timezone
from feedgen.feed import FeedGenerator
from flask import Blueprint, Response, current_app, request, render_template
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
from listenbrainz.db.fresh_releases import get_fresh_releases as db_get_fresh_releases

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

    interval = request.args.get("interval", 60)
    if interval:
        try:
            interval = int(interval)
        except ValueError:
            return Response(status=400)
    if interval < 1:
        return Response(status=400)

    from_ts = datetime.now() - timedelta(minutes=interval)
    listens, _, _ = timescale_connection._ts.fetch_listens(user, from_ts=from_ts)

    server_root_url = current_app.config["SERVER_ROOT_URL"]

    fg = FeedGenerator()
    fg.id(f"{server_root_url}/user/{user_name}")
    fg.title(f"Listens for {user_name} - ListenBrainz")
    fg.author({"name": "ListenBrainz"})
    fg.link(href=f"{server_root_url}/user/{user_name}", rel="alternate")
    fg.link(
        href=f"{server_root_url}/syndication-feed/user/{user_name}/listens",
        rel="self",
    )
    fg.logo(f"{server_root_url}/static/img/listenbrainz_logo_icon.svg")
    fg.language("en")

    # newer listen comes first
    for listen in reversed(listens):
        fe = fg.add_entry()
        # according to spec, ids don't have to be deferencable.
        fe.id(
            f"{server_root_url}/syndication-feed/user/{user_name}/listens/{listen.ts_since_epoch}/{listen.data['track_name']}"
        )
        fe.title(f"{listen.data['track_name']} - {listen.data['artist_name']}")

        _content = render_template(
            "atom/listens.html",
            server_root_url=server_root_url,
            user_name=listen.user_name,
            track_name=listen.data["track_name"],
            recording_mbid=listen.data["additional_info"].get("recording_mbid"),
            artist_name=listen.data["artist_name"],
            artist_mbid=(
                listen.data["additional_info"].get("artist_mbids")[0]
                if listen.data["additional_info"].get("artist_mbids")
                else None
            ),  # needs mbid mapping
            release_mbid=listen.data["additional_info"].get("release_mbid"),
            release_name=listen.data["release_name"],
        )
        fe.content(
            content=_content,
            type="html",
        )

        fe.published(listen.timestamp)
        fe.updated(listen.timestamp)

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
        db_releases, _ = get_sitewide_fresh_releases(
            ts_conn, date.today(), days, "release_date", past, future
        )
    except Exception as e:
        current_app.logger.error("Server failed to get latest release: {}".format(e))
        raise Response(status=500)

    fg = FeedGenerator()
    fg.id(f"https://listenbrainz.org/explore/fresh-releases")
    fg.title(f"Fresh Releases - ListenBrainz")
    fg.author({"name": "ListenBrainz"})
    fg.link(href=f"https://listenbrainz.org/explore/fresh-releases", rel="alternate")
    fg.link(
        href=f"https://listenbrainz.org/syndication-feed/fresh_releases",
        rel="self",
    )
    fg.logo("https://listenbrainz.org/static/img/listenbrainz_logo_icon.svg")
    fg.language("en")

    for r in db_releases:
        release_name = r.release_name
        artist_credit_name = r.artist_credit_name
        time = r.release_date.strftime("%Y-%m-%d")

        fe = fg.add_entry()
        fe.id(
            f"https://listenbrainz.org/syndication-feed/fresh_releases/{time}/{artist_credit_name}/{release_name}"
        )
        fe.title(f"{release_name} by {artist_credit_name}")

        _content = render_template(
            "atom/fresh_releases.html",
            artist_credit_name=artist_credit_name,
            release_name=release_name,
            time=time,
        )

        fe.content(
            content=_content,
            type="html",
        )
        t = datetime.combine(r.release_date, datetime.min.time())
        fe.published(t.replace(tzinfo=timezone.utc))
        fe.updated(t.replace(tzinfo=timezone.utc))

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.route("/user/<user_name>/fresh_releases", methods=["GET"])
@crossdomain
def get_releases(user_name):
    """
    Get fresh releases for a user, sorted by release date.

    :param past: Whether to show releases in the past. Default True.
    :param future: Whether to show releases in the future. Default True.
    :statuscode 200: The feed was successfully generated.
    :statuscode 400: Bad request.
    :statuscode 404: The user does not exist.
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        return Response(status=404)

    past = _parse_bool_arg("past", True)
    future = _parse_bool_arg("future", True)

    data = db_get_fresh_releases(user["id"])
    releases = data["releases"] if data else []
    releases = sorted(releases, key=lambda k: k.get("release_date", ""))

    if not past:
        releases = [
            r
            for r in releases
            if "release_date" in r
            and datetime.strptime(r["release_date"], "%Y-%m-%d").date() >= date.today()
        ]

    if not future:
        releases = [
            r
            for r in releases
            if "release_date" in r
            and datetime.strptime(r["release_date"], "%Y-%m-%d").date() <= date.today()
        ]

    fg = FeedGenerator()
    fg.id(f"https://listenbrainz.org/user/{user_name}/fresh_releases")
    fg.title(f"Fresh Releases for {user_name} - ListenBrainz")
    fg.author({"name": "ListenBrainz"})
    fg.link(href=f"https://listenbrainz.org/explore/fresh-releases", rel="alternate")
    fg.link(
        href=f"https://listenbrainz.org/syndication-feed/user/{user_name}/fresh_releases",
        rel="self",
    )
    fg.logo("https://listenbrainz.org/static/img/listenbrainz_logo_icon.svg")
    fg.language("en")

    for r in releases:
        release_name = r["release_name"]
        artist_credit_name = r["artist_credit_name"]
        time = r["release_date"]

        fe = fg.add_entry()
        fe.id(
            f"https://listenbrainz.org/syndication-feed/user/{user_name}/fresh_releases/{time}/{artist_credit_name}/{release_name}"
        )
        fe.title(f"{release_name} by {artist_credit_name}")

        _content = render_template(
            "atom/fresh_releases.html",
            artist_credit_name=artist_credit_name,
            release_name=release_name,
            time=time,
        )

        fe.content(
            content=_content,
            type="html",
        )
        t = datetime.combine(datetime.strptime(time, "%Y-%m-%d"), datetime.min.time())
        fe.published(t.replace(tzinfo=timezone.utc))
        fe.updated(t.replace(tzinfo=timezone.utc))

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")
