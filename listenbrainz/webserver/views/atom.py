from datetime import datetime, timedelta, date, timezone
from feedgen.feed import FeedGenerator
from flask import Blueprint, Response, current_app, request, render_template, url_for
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

DEFAULT_MINUTES_OF_LISTENS = 60
MAX_MINUTES_OF_LISTENS = 7 * 24 * 60  # a week


atom_bp = Blueprint("atom", __name__)


def _external_url_for(endpoint, **values):
    return url_for(endpoint, _external=True, **values)


@atom_bp.route("/user/<user_name>/listens", methods=["GET"])
@crossdomain
@ratelimit()
@api_listenstore_needed
def get_listens(user_name):
    """
    Get listens feed for a user.

    :param minutes: The time interval in minutes from current time to fetch listens for.
                    For example, if minutes=60, listens from the last hour will be fetched. Default is 60.
    :statuscode 200: The feed was successfully generated.
    :statuscode 400: Bad request.
    :statuscode 404: The user does not exist.
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        return Response(status=404)

    minutes = request.args.get("minutes", DEFAULT_MINUTES_OF_LISTENS)
    if minutes:
        try:
            minutes = int(minutes)
        except ValueError:
            return Response(status=400)
    if minutes < 1 or minutes > MAX_MINUTES_OF_LISTENS:
        return Response(status=400)

    # estimate limit from minutes, assuming 1 listen per minute.
    # mostly likely there won't be that much listens, but with such padding
    # it's less likely for feed readers to miss listens.
    limit = minutes

    to_ts = datetime.now()
    listens, _, _ = timescale_connection._ts.fetch_listens(user, to_ts=to_ts, limit=limit)

    fg = FeedGenerator()
    fg.id(_external_url_for("atom.get_listens", user_name=user_name))
    fg.title(f"Listens for {user_name} - ListenBrainz")
    fg.author({"name": "ListenBrainz"})
    fg.link(
        href=_external_url_for("user.index", path="", user_name=user_name),
        rel="alternate",
    )
    fg.link(
        href=_external_url_for("atom.get_listens", user_name=user_name),
        rel="self",
    )
    fg.logo(_external_url_for("static", filename="img/listenbrainz_logo_icon.svg"))
    fg.language("en")

    # newer listen comes first
    for listen in reversed(listens):
        track_name = listen.data["track_name"]
        recording_mbid = listen.data["additional_info"].get("recording_mbid")
        artist_name = listen.data["artist_name"]
        artist_mbid = (
            listen.data["additional_info"].get("artist_mbids")[0]
            if listen.data["additional_info"].get("artist_mbids")
            else None
        )

        fe = fg.add_entry()
        # according to spec, ids don't have to be deferencable.
        fe.id(
            f"{_external_url_for('atom.get_listens', user_name=user_name)}/{listen.ts_since_epoch}/{track_name}"
        )
        fe.title(f"{track_name} - {artist_name}")

        _content = render_template(
            "atom/listens.html",
            user={
                "href": _external_url_for("user.index", path="", user_name=user_name),
                "user_name": user_name,
            },
            track={
                "href": f"https://musicbrainz.org/recording/{recording_mbid}",
                "track_name": track_name,
            },
            artist={
                "href": _external_url_for("artist.artist_page", path=artist_mbid),
                "artist_name": artist_name,
            },
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
    :statuscode 200: The feed was successfully generated.
    :statuscode 400: Bad request.
    :statuscode 500: Server failed to get latest release.
    :resheader Content-Type: *application/atom+xml*
    """
    days = _parse_int_arg("days", DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS)
    if days < 1 or days > MAX_NUMBER_OF_FRESH_RELEASE_DAYS:
        return Response(status=400)

    try:
        # Get past fresh releases sorted by release date
        db_releases, _ = get_sitewide_fresh_releases(
            ts_conn, date.today(), days, "release_date", True, False
        )
    except Exception as e:
        current_app.logger.error("Server failed to get latest release: {}".format(e))
        return Response(status=500)

    fg = FeedGenerator()
    fg.id(_external_url_for("atom.get_fresh_releases"))
    fg.title(f"Fresh Releases - ListenBrainz")
    fg.author({"name": "ListenBrainz"})
    fg.link(
        href=_external_url_for("explore.index", path="fresh-releases"), rel="alternate"
    )
    fg.link(
        href=_external_url_for("atom.get_fresh_releases"),
        rel="self",
    )
    fg.logo(_external_url_for("static", filename="img/listenbrainz_logo_icon.svg"))
    fg.language("en")

    for r in db_releases:
        release_name = r.release_name
        artist_credit_name = r.artist_credit_name
        release_date = r.release_date
        release_mbid = r.release_mbid
        artist_mbid = r.artist_mbids[0] if r.artist_mbids else None

        _t = datetime.combine(release_date, datetime.min.time())
        _t_with_tz = _t.replace(tzinfo=timezone.utc)
        _uts = int(_t.timestamp())

        fe = fg.add_entry()
        fe.id(
            f"{_external_url_for('atom.get_fresh_releases')}/{_uts}/{artist_credit_name}/{release_name}"
        )
        fe.title(f"{release_name} by {artist_credit_name}")

        _content = render_template(
            "atom/fresh_releases.html",
            artist={
                "href": _external_url_for("artist.artist_page", path=artist_mbid),
                "artist_name": artist_credit_name,
            },
            release={
                "href": f"https://musicbrainz.org/release/{release_mbid}",
                "release_name": release_name,
            },
        )
        fe.content(
            content=_content,
            type="html",
        )

        fe.published(_t_with_tz)
        fe.updated(_t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.route("/user/<user_name>/fresh_releases", methods=["GET"])
@crossdomain
def get_releases(user_name):
    """
    Get fresh releases for a user, sorted by release date.

    :statuscode 200: The feed was successfully generated.
    :statuscode 400: Bad request.
    :statuscode 404: The user does not exist.
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        return Response(status=404)

    data = db_get_fresh_releases(user["id"])
    releases = sorted(
        [
            r
            for r in data["releases"]
            if "release_date" in r
            and datetime.strptime(r["release_date"], "%Y-%m-%d").date()
            <= date.today()  # only include past releases
        ],
        key=lambda k: k.get("release_date", ""),  # sort by release date
    )

    fg = FeedGenerator()
    fg.id(_external_url_for("atom.get_releases", user_name=user_name))
    fg.title(f"Fresh Releases for {user_name} - ListenBrainz")
    fg.author({"name": "ListenBrainz"})
    fg.link(
        href=_external_url_for("explore.index", path="fresh-releases"), rel="alternate"
    )
    fg.link(
        href=_external_url_for("atom.get_releases", user_name=user_name),
        rel="self",
    )
    fg.logo(_external_url_for("static", filename="img/listenbrainz_logo_icon.svg"))
    fg.language("en")

    for r in releases:
        release_name = r["release_name"]
        artist_credit_name = r["artist_credit_name"]
        release_date = r["release_date"]
        release_mbid = r["release_mbid"]
        artist_mbid = r["artist_mbids"][0] if r["artist_mbids"] else None

        _t = datetime.combine(
            datetime.strptime(release_date, "%Y-%m-%d"), datetime.min.time()
        )
        _t_with_tz = _t.replace(tzinfo=timezone.utc)
        _uts = int(_t.timestamp())

        fe = fg.add_entry()
        fe.id(
            f"{_external_url_for('atom.get_releases', user_name=user_name)}/{_uts}/{artist_credit_name}/{release_name}"
        )
        fe.title(f"{release_name} by {artist_credit_name}")

        _content = render_template(
            "atom/fresh_releases.html",
            artist={
                "href": _external_url_for("artist.artist_page", path=artist_mbid),
                "artist_name": artist_credit_name,
            },
            release={
                "href": f"https://musicbrainz.org/release/{release_mbid}",
                "release_name": release_name,
            },
        )
        fe.content(
            content=_content,
            type="html",
        )

        fe.published(_t_with_tz)
        fe.updated(_t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")
