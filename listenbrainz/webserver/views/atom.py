from datetime import datetime, date, timedelta, timezone
from feedgen.feed import FeedGenerator
from flask import Blueprint, Response, current_app, request, render_template, url_for
from listenbrainz.webserver.decorators import crossdomain, api_listenstore_needed
from brainzutils.ratelimit import ratelimit
import listenbrainz.db.user as db_user
from listenbrainz.webserver import db_conn, timescale_connection
from listenbrainz.webserver.views.api_tools import (
    _parse_int_arg,
    get_non_negative_param,
)
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.db.fresh_releases import get_sitewide_fresh_releases
from listenbrainz.db.fresh_releases import get_fresh_releases as db_get_fresh_releases
from data.model.common_stat import StatisticsRange
from listenbrainz.webserver.views.stats_api import _is_valid_range
import listenbrainz.db.stats as db_stats
from data.model.user_entity import EntityRecord
from listenbrainz.webserver.views.api_tools import (
    DEFAULT_ITEMS_PER_GET,
    MAX_ITEMS_PER_GET,
)
from werkzeug.exceptions import NotFound, BadRequest, InternalServerError

DEFAULT_MINUTES_OF_LISTENS = 60
MAX_MINUTES_OF_LISTENS = 7 * 24 * 60  # a week
DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS = 3
MAX_NUMBER_OF_FRESH_RELEASE_DAYS = 30


atom_bp = Blueprint("atom", __name__)


def _external_url_for(endpoint, **values):
    """
    A simple wrapper around Flask's url_for that generates an absolute URL.
    """
    return url_for(endpoint, _external=True, **values)


def _is_daily_updated_stats(stats_range: str) -> bool:
    """
    Determine if the stats are updated daily.
    If so, we can use the timestamp of the last updated stats to generate a new entry for each day.
    """
    return stats_range in [
        StatisticsRange.this_week.value,
        StatisticsRange.this_month.value,
        StatisticsRange.this_year.value,
        StatisticsRange.all_time.value,
    ]


def _get_stats_feed_title(user_name: str, entity: str, stats_range: str) -> str:
    """
    A central place to generate feed titles for stats feeds.
    """
    _entity_descriptions = {
        "artists": "Top Artists",
        "release_groups": "Top Albums",
        "recordings": "Top Tracks",
    }
    _stats_range_descriptions = {
        StatisticsRange.this_week.value: "This Week's",
        StatisticsRange.this_month.value: "This Month's",
        StatisticsRange.this_year.value: "This Year's",
        StatisticsRange.week.value: "Weekly",
        StatisticsRange.month.value: "Monthly",
        StatisticsRange.quarter.value: "Quarterly",
        StatisticsRange.half_yearly.value: "Half Yearly",
        StatisticsRange.year.value: "Yearly",
        StatisticsRange.all_time.value: "All Time",
    }
    return f"{_stats_range_descriptions[stats_range]} {_entity_descriptions[entity]} for {user_name} - ListenBrainz"


def _get_stats_entry_title(stats_range: str, timestamp: int) -> str:
    """
    A central place to generate feed entry titles for stats feeds.
    """
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    if stats_range in [StatisticsRange.this_week.value, StatisticsRange.week.value]:
        return f"Week {dt.isocalendar()[1]}"
    elif stats_range in [StatisticsRange.this_month.value, StatisticsRange.month.value]:
        return dt.strftime("%B %Y")
    elif stats_range in [StatisticsRange.this_year.value, StatisticsRange.year.value]:
        return dt.strftime("%Y")
    elif stats_range in [StatisticsRange.quarter.value]:
        return f"Q{int((dt.month - 1) / 3) + 1} {dt.year}"
    elif stats_range in [StatisticsRange.half_yearly.value]:
        return f"H{int((dt.month - 1) / 6) + 1} {dt.year}"
    elif stats_range in [StatisticsRange.all_time.value]:
        return "All Time"
    assert False, f"Invalid stats_range: {stats_range}"


def _init_feed(id, title, self_url, alternate_url):
    """
    Initialize a feed with common attributes.
    """
    fg = FeedGenerator()
    fg.id(id)
    fg.title(title)
    fg.author({"name": "ListenBrainz"})
    fg.link(href=alternate_url, rel="alternate")
    fg.link(href=self_url, rel="self")
    fg.logo(_external_url_for("static", filename="img/listenbrainz_logo_icon.svg"))
    fg.language("en")
    return fg


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
        return NotFound("User not found")

    minutes = request.args.get("minutes", DEFAULT_MINUTES_OF_LISTENS)
    if minutes:
        try:
            minutes = int(minutes)
        except ValueError:
            return BadRequest("Invalid value for minutes")
    if minutes < 1 or minutes > MAX_MINUTES_OF_LISTENS:
        return BadRequest("Value of minutes is out of range")

    to_ts = datetime.now()
    from_ts = to_ts - timedelta(minutes=minutes)
    listens, _, _ = timescale_connection._ts.fetch_listens(
        user, from_ts=from_ts, to_ts=to_ts, limit=MAX_ITEMS_PER_GET
    )

    fg = _init_feed(
        _external_url_for(".get_listens", user_name=user_name),
        f"Listens for {user_name} - ListenBrainz",
        _external_url_for("user.index", path="", user_name=user_name),
        _external_url_for(".get_listens", user_name=user_name),
    )

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
            f"{_external_url_for('.get_listens', user_name=user_name)}/{listen.ts_since_epoch}/{track_name}"
        )
        fe.title(f"{track_name} - {artist_name}")

        content = render_template(
            "atom/listens.html",
            user_page_url=_external_url_for("user.index", path="", user_name=user_name),
            user_name=user_name,
            recording_mb_page_base_url="https://musicbrainz.org/recording/",
            track_name=track_name,
            recording_mbid=recording_mbid,
            artist_page_base_url=_external_url_for("artist.artist_page", path=""),
            artist_mbid=artist_mbid,
            artist_name=artist_name,
        )
        fe.content(
            content=content,
            type="html",
        )

        fe.published(listen.timestamp)
        fe.updated(listen.timestamp)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.route("/fresh-releases", methods=["GET"])
@crossdomain
@ratelimit()
def get_fresh_releases():
    """
    Get site-wide fresh releases.

    :param days: The number of days of fresh releases to show.
                 Default `DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS` days. Max `MAX_NUMBER_OF_FRESH_RELEASE_DAYS` days.
    :statuscode 200: The feed was successfully generated.
    :statuscode 400: Bad request.
    :statuscode 500: Server failed to get latest release.
    :resheader Content-Type: *application/atom+xml*
    """
    days = _parse_int_arg("days", DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS)
    if days < 1 or days > MAX_NUMBER_OF_FRESH_RELEASE_DAYS:
        return BadRequest("Value of days is out of range")

    try:
        # Get past fresh releases sorted by release date
        db_releases, _ = get_sitewide_fresh_releases(
            ts_conn, date.today(), days, "release_date", True, False
        )
    except Exception as e:
        current_app.logger.error("Server failed to get latest release: {}".format(e))
        return InternalServerError("Server failed to get latest release")

    fg = _init_feed(
        _external_url_for(".get_fresh_releases"),
        "Fresh Releases - ListenBrainz",
        _external_url_for("explore.index", path="fresh-releases"),
        _external_url_for(".get_fresh_releases"),
    )

    for r in db_releases:
        release_name = r.release_name
        artist_credit_name = r.artist_credit_name
        release_date = r.release_date
        release_mbid = r.release_mbid
        artist_mbid = r.artist_mbids[0] if r.artist_mbids else None

        t = datetime.combine(release_date, datetime.min.time())
        t_with_tz = t.replace(tzinfo=timezone.utc)
        uts = int(t.timestamp())

        fe = fg.add_entry()
        fe.id(
            f"{_external_url_for('.get_fresh_releases')}/{uts}/{artist_credit_name}/{release_name}"
        )
        fe.title(f"{release_name} by {artist_credit_name}")

        content = render_template(
            "atom/fresh_releases.html",
            release_mb_page_base_url="https://musicbrainz.org/release/",
            release_name=release_name,
            release_mbid=release_mbid,
            artist_page_base_url=_external_url_for("artist.artist_page", path=""),
            artist_mbid=artist_mbid,
            artist_name=artist_credit_name,
            expore_fresh_releases_url=_external_url_for(
                "explore.index", path="fresh-releases"
            ),
        )
        fe.content(
            content=content,
            type="html",
        )

        fe.published(t_with_tz)
        fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.route("/user/<user_name>/fresh-releases", methods=["GET"])
@crossdomain
def get_user_fresh_releases(user_name):
    """
    Get fresh releases for a user, sorted by release date.

    :statuscode 200: The feed was successfully generated.
    :statuscode 404: The user does not exist.
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        return NotFound("User not found")

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

    fg = _init_feed(
        _external_url_for(".get_user_fresh_releases", user_name=user_name),
        f"Fresh Releases for {user_name} - ListenBrainz",
        _external_url_for("explore.index", path="fresh-releases"),
        _external_url_for(".get_user_fresh_releases", user_name=user_name),
    )

    for r in releases:
        release_name = r["release_name"]
        artist_credit_name = r["artist_credit_name"]
        release_date = r["release_date"]
        release_mbid = r["release_mbid"]
        artist_mbid = r["artist_mbids"][0] if r["artist_mbids"] else None

        t = datetime.combine(
            datetime.strptime(release_date, "%Y-%m-%d"), datetime.min.time()
        )
        t_with_tz = t.replace(tzinfo=timezone.utc)
        uts = int(t.timestamp())

        fe = fg.add_entry()
        fe.id(
            f"{_external_url_for('.get_user_fresh_releases', user_name=user_name)}/{uts}/{artist_credit_name}/{release_name}"
        )
        fe.title(f"{release_name} by {artist_credit_name}")

        content = render_template(
            "atom/fresh_releases.html",
            release_mb_page_base_url="https://musicbrainz.org/release/",
            release_name=release_name,
            release_mbid=release_mbid,
            artist_page_base_url=_external_url_for("artist.artist_page", path=""),
            artist_mbid=artist_mbid,
            artist_name=artist_credit_name,
            explore_fresh_releases_url=_external_url_for(
                "explore.index", path="fresh-releases"
            ),
        )
        fe.content(
            content=content,
            type="html",
        )

        fe.published(t_with_tz)
        fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


def _get_entity_stats(user_id: str, entity: str, range: str, count: int):
    stats = db_stats.get(user_id, entity, range, EntityRecord)
    if stats is None:
        return None, None, None

    count = min(count, MAX_ITEMS_PER_GET)
    entity_list = [x.dict() for x in stats.data.__root__[:count]]
    return entity_list, stats.to_ts, stats.last_updated


@atom_bp.route("/user/<user_name>/stats/top-artists")
@crossdomain
@ratelimit()
def get_artist_stats(user_name):
    """
    Get top artists for a user.

    :param count: Optional, number of artists to return, Default: :data:`~DEFAULT_STATS_ITEMS_PER_GET`
        Max: :data:`~MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``week``
    :type range: ``str``
    :statuscode 200: The feed was successfully generated.
    :statuscode 204: Statistics for the user haven't been calculated.
    :statuscode 400: Bad request
    :statuscode 404: User not found
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise NotFound("User not found")

    range = request.args.get("range", default="week")
    if not _is_valid_range(range):
        return BadRequest("Invalid range")

    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    entity_list, to_ts, last_updated = _get_entity_stats(
        user["id"], "artists", range, count
    )
    if entity_list is None:
        return Response(
            status=204, response="Statistics for the user haven't been calculated."
        )

    fg = _init_feed(
        _external_url_for(".get_artist_stats", user_name=user_name),
        _get_stats_feed_title(user_name, "artists", range),
        _external_url_for("user.stats", user_name=user_name),
        _external_url_for(".get_artist_stats", user_name=user_name),
    )

    # this_* stats are updated daily, so we can use the timestamp of the last updated stats,
    # and they will be a new entry for each day, different entry id each day.
    # otherwise, we use the timestamp of the end of the range, and it will be a new entry for each range.
    if _is_daily_updated_stats(range):
        t = last_updated
    else:
        t = to_ts
    dt = datetime.fromtimestamp(t)
    t_with_tz = dt.replace(tzinfo=timezone.utc)

    fe = fg.add_entry()
    fe.id(f"{_external_url_for('.get_artist_stats', user_name=user_name)}/{range}/{t}")
    fe.title(
        _get_stats_entry_title(range, to_ts - 60)
    )  # minus 1 minute to situate the entry in the right range

    content = render_template(
        "atom/top_artists.html",
        artists=entity_list,
        artist_page_base_url=_external_url_for("artist.artist_page", path=""),
    )
    fe.content(
        content=content,
        type="html",
    )

    fe.published(t_with_tz)
    fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.route("/user/<user_name>/stats/top-albums")
@crossdomain
@ratelimit()
def get_release_group_stats(user_name):
    """
    Get top albums for a user.

    :param count: Optional, number of releases to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: The feed was successfully generated.
    :statuscode 204: Statistics for the user haven't been calculated.
    :statuscode 400: Bad request
    :statuscode 404: User not found
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise NotFound("User not found")

    range = request.args.get("range", default="week")
    if not _is_valid_range(range):
        return BadRequest("Invalid range")

    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    entity_list, to_ts, last_updated = _get_entity_stats(
        user["id"], "release_groups", range, count
    )
    if entity_list is None:
        return Response(
            status=204, response="Statistics for the user haven't been calculated."
        )

    fg = _init_feed(
        _external_url_for(".get_release_group_stats", user_name=user_name),
        _get_stats_feed_title(user_name, "release_groups", range),
        _external_url_for("user.stats", user_name=user_name),
        _external_url_for(".get_release_group_stats", user_name=user_name),
    )

    if _is_daily_updated_stats(range):
        t = last_updated
    else:
        t = to_ts
    dt = datetime.fromtimestamp(t)
    t_with_tz = dt.replace(tzinfo=timezone.utc)

    fe = fg.add_entry()
    fe.id(
        f"{_external_url_for('.get_release_group_stats', user_name=user_name)}/{range}/{t}"
    )
    fe.title(
        _get_stats_entry_title(range, to_ts - 60)
    )  # minus 1 minute to situate the entry in the right range

    content = render_template(
        "atom/top_albums.html",
        release_groups=entity_list,
        artist_page_base_url=_external_url_for("artist.artist_page", path=""),
    )
    fe.content(
        content=content,
        type="html",
    )

    fe.published(t_with_tz)
    fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.route("/user/<user_name>/stats/top-tracks")
@crossdomain
@ratelimit()
def get_recording_stats(user_name):
    """
    Get top tracks for a user.

    :param count: Optional, number of recordings to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: The feed was successfully generated.
    :statuscode 204: Statistics for the user haven't been calculated.
    :statuscode 400: Bad request
    :statuscode 404: User not found
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise NotFound("User not found")

    range = request.args.get("range", default="week")
    if not _is_valid_range(range):
        return BadRequest("Invalid range")

    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    entity_list, to_ts, last_updated = _get_entity_stats(
        user["id"], "recordings", range, count
    )
    if entity_list is None:
        return Response(
            status=204, response="Statistics for the user haven't been calculated."
        )

    fg = _init_feed(
        _external_url_for(".get_recording_stats", user_name=user_name),
        _get_stats_feed_title(user_name, "recordings", range),
        _external_url_for("user.stats", user_name=user_name),
        _external_url_for(".get_recording_stats", user_name=user_name),
    )

    if _is_daily_updated_stats(range):
        t = last_updated
    else:
        t = to_ts
    dt = datetime.fromtimestamp(t)
    t_with_tz = dt.replace(tzinfo=timezone.utc)

    fe = fg.add_entry()
    fe.id(
        f"{_external_url_for('.get_recording_stats', user_name=user_name)}/{range}/{t}"
    )
    fe.title(
        _get_stats_entry_title(range, to_ts - 60)
    )  # minus 1 minute to situate the entry in the right range

    content = render_template(
        "atom/top_tracks.html",
        tracks=entity_list,
        artist_page_base_url=_external_url_for("artist.artist_page", path=""),
    )
    fe.content(
        content=content,
        type="html",
    )

    fe.published(t_with_tz)
    fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")
