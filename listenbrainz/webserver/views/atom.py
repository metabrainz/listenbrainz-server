from datetime import datetime, date, timedelta, timezone
from feedgen.feed import FeedGenerator
from flask import Blueprint, Response, current_app, request, render_template, url_for
import listenbrainz.db.user_relationship as db_user_relationship
from listenbrainz.db.model.user_timeline_event import UserTimelineEventType
from listenbrainz.webserver.decorators import crossdomain, api_listenstore_needed
from brainzutils.ratelimit import ratelimit
import listenbrainz.db.user as db_user
from listenbrainz.webserver import db_conn, timescale_connection
from listenbrainz.webserver.views.api_tools import (
    _parse_int_arg,
    get_non_negative_param,
    is_valid_uuid,
)
from listenbrainz.webserver import db_conn, ts_conn, API_PREFIX
from listenbrainz.db.fresh_releases import get_sitewide_fresh_releases
from listenbrainz.db.fresh_releases import get_fresh_releases as db_get_fresh_releases
from data.model.common_stat import StatisticsRange
from listenbrainz.webserver.views.playlist_api import fetch_playlist_recording_metadata
from listenbrainz.webserver.views.stats_api import _is_valid_range
from listenbrainz.webserver.views.art_api import cover_art_custom_stats, cover_art_grid_stats
import listenbrainz.db.stats as db_stats
from data.model.user_entity import EntityRecord
from listenbrainz.webserver.views.api_tools import (
    DEFAULT_ITEMS_PER_GET,
    MAX_ITEMS_PER_GET,
)
from listenbrainz.webserver.views.user_timeline_event_api import (
    get_feed_events_for_user,
)
from werkzeug.exceptions import NotFound, BadRequest, InternalServerError
import listenbrainz.db.playlist as db_playlist
from listenbrainz.art.cover_art_generator import (
    MIN_IMAGE_SIZE,
    MAX_IMAGE_SIZE,
    MIN_DIMENSION,
    MAX_DIMENSION,
)

DEFAULT_MINUTES_OF_LISTENS = 60
MAX_MINUTES_OF_LISTENS = 7 * 24 * 60  # a week
DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS = 3
MAX_NUMBER_OF_FRESH_RELEASE_DAYS = 30
RECOMMENDATION_TYPES = (
    "weekly-jams",
    "weekly-exploration",
    "daily-jams",
)
STATS_RANGE_DESCRIPTIONS = {
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
DEFAULT_MINUTES_OF_EVENTS = 60


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
    return f"{STATS_RANGE_DESCRIPTIONS[stats_range]} {_entity_descriptions[entity]} for {user_name} - ListenBrainz"


def _get_stats_entry_title(stats_range: str, timestamp: int) -> str:
    """
    A central place to generate feed entry titles for stats feeds.
    """
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    if stats_range in [StatisticsRange.this_week.value, StatisticsRange.week.value]:
        iso_year, iso_week, iso_day = dt.isocalendar()
        start_of_week = date.fromisocalendar(iso_year,iso_week,day=1).strftime("%a %d %b")
        end_of_week = date.fromisocalendar(iso_year,iso_week,day=7).strftime("%a %d %b")
        return f"Week {iso_week} ({start_of_week} - {end_of_week} {iso_year})"
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


def _get_cover_art_feed_title(
    user_name: str, stats_range: str, art_type: str, custom_name: str = None
) -> str:
    """
    Generate feed titles specifically for cover art feeds.
    """
    art_titles = {
        "designer-top-5": "Designer Top 5",
        "designer-top-10": "Designer Top 10",
        "lps-on-the-floor": "LPs on the Floor",
        "grid-stats": "Album Grid",
        "grid-stats-special": "Album Grid Alt",
    }

    range_description = STATS_RANGE_DESCRIPTIONS.get(
        stats_range, stats_range.capitalize()
    )

    if art_type == "grid":
        title = "Grid Cover Art"
    elif art_type == "custom" and custom_name in art_titles:
        title = art_titles[custom_name]
    else:
        assert False, f"Invalid art_type: {art_type}"

    return f"{range_description} {title} for {user_name} - ListenBrainz"


def _init_feed(id, title, alternate_url, self_url):
    """
    Initialize a feed with common attributes.
    """
    fg = FeedGenerator()
    fg.id(id)
    fg.title(title)
    fg.author({"name": "ListenBrainz"})
    # Self link should be that of the RSS feed
    fg.link(href=self_url, rel="self")
    # Alternate link should be the page this info is on
    fg.link(href=alternate_url, rel="alternate")
    fg.logo(_external_url_for("static", filename="img/listenbrainz_logo_icon.svg"))
    fg.language("en")
    return fg


@atom_bp.get("/user/<user_name>/listens")
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
    
    this_feed_url = _external_url_for(".get_listens", user_name=user_name)
    user_dashboard_url = _external_url_for("user.index", path="", user_name=user_name)

    fg = _init_feed(
        this_feed_url,
        f"Listens for {user_name} - ListenBrainz",
        user_dashboard_url,
        this_feed_url,
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
            f"{this_feed_url}/{listen.ts_since_epoch}/{track_name}"
        )
        fe.title(f"{track_name} - {artist_name}")
        fe.link(href=user_dashboard_url, rel="alternate")

        content = render_template(
            "atom/listens.html",
            user_page_url=user_dashboard_url,
            user_name=user_name,
            recording_mb_page_base_url="https://musicbrainz.org/recording/",
            track_name=track_name,
            recording_mbid=recording_mbid,
            artist_page_base_url=_external_url_for(
                "artist.artist_page", path=""),
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


@atom_bp.get("/fresh-releases")
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
        current_app.logger.error(
            "Server failed to get latest release: {}".format(e))
        return InternalServerError("Server failed to get latest release")

    this_feed_url = _external_url_for(".get_fresh_releases")

    fg = _init_feed(
        this_feed_url,
        "Fresh Releases - ListenBrainz",
        _external_url_for("explore.index", path="fresh-releases"),
        this_feed_url,
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
            f"{this_feed_url}/{uts}/{artist_credit_name}/{release_name}"
        )
        fe.title(f"{release_name} by {artist_credit_name}")
        fe.link(href=f"{_external_url_for('release.release_page')}{release_mbid}", rel="alternate")

        content = render_template(
            "atom/fresh_releases.html",
            release_lb_page_base_url=_external_url_for('release.release_page'),
            release_name=release_name,
            release_mbid=release_mbid,
            artist_page_base_url=_external_url_for(
                "artist.artist_page", path=""),
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


@atom_bp.get("/user/<user_name>/fresh-releases")
@crossdomain
@ratelimit()
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
    releases = []
    if data and "releases" in data:
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

    this_feed_url = _external_url_for(".get_user_fresh_releases", user_name=user_name)

    fg = _init_feed(
        this_feed_url,
        f"Fresh Releases for {user_name} - ListenBrainz",
        _external_url_for("explore.index", path="fresh-releases"),
        this_feed_url,
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
            f"{this_feed_url}/{uts}/{artist_credit_name}/{release_name}"
        )
        fe.title(f"{release_name} by {artist_credit_name}")
        fe.link(href=f"{_external_url_for('release.release_page')}{release_mbid}", rel="alternate")

        content = render_template(
            "atom/fresh_releases.html",
            release_lb_page_base_url=_external_url_for('release.release_page'),
            release_name=release_name,
            release_mbid=release_mbid,
            artist_page_base_url=_external_url_for(
                "artist.artist_page", path=""),
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


@atom_bp.get("/user/<user_name>/stats/top-artists")
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
    this_feed_url = _external_url_for(".get_artist_stats", user_name=user_name, range=range)
    user_stats_url = _external_url_for("user.index", path="stats/top-artists", user_name=user_name, range=range)
    
    fg = _init_feed(
        this_feed_url,
        _get_stats_feed_title(user_name, "artists", range),
        user_stats_url,
        this_feed_url,
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
    fe.id(f"{this_feed_url}/{t}")
    fe.title(
        _get_stats_entry_title(range, to_ts - 60)
    )  # minus 1 minute to situate the entry in the right range
    fe.link(href=user_stats_url, rel="alternate")

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


@atom_bp.get("/user/<user_name>/stats/top-albums")
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

    this_feed_url = _external_url_for(".get_release_group_stats", user_name=user_name, range=range)
    user_stats_url = _external_url_for("user.index", path="stats/top-albums", user_name=user_name, range=range)

    fg = _init_feed(
        this_feed_url,
        _get_stats_feed_title(user_name, "release_groups", range),
        user_stats_url,
        this_feed_url,
    )

    if _is_daily_updated_stats(range):
        t = last_updated
    else:
        t = to_ts
    dt = datetime.fromtimestamp(t)
    t_with_tz = dt.replace(tzinfo=timezone.utc)

    fe = fg.add_entry()
    fe.id(
        f"{this_feed_url}/{t}"
    )
    fe.title(
        _get_stats_entry_title(range, to_ts - 60)
    )  # minus 1 minute to situate the entry in the right range
    fe.link(href=user_stats_url, rel="alternate")

    content = render_template(
        "atom/top_albums.html",
        release_groups=entity_list,
        artist_page_base_url=_external_url_for("artist.artist_page", path=""),
        album_page_base_url=_external_url_for("album.album_page", path=""),
    )
    fe.content(
        content=content,
        type="html",
    )

    fe.published(t_with_tz)
    fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.get("/user/<user_name>/stats/top-tracks")
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

    this_feed_url = _external_url_for(".get_recording_stats", user_name=user_name, range=range)
    user_stats_url = _external_url_for("user.index", path="stats/top-tracks", user_name=user_name, range=range)

    fg = _init_feed(
        this_feed_url,
        _get_stats_feed_title(user_name, "recordings", range),
        user_stats_url,
        this_feed_url,
    )

    if _is_daily_updated_stats(range):
        t = last_updated
    else:
        t = to_ts
    dt = datetime.fromtimestamp(t)
    t_with_tz = dt.replace(tzinfo=timezone.utc)

    fe = fg.add_entry()
    fe.id(
        f"{this_feed_url}/{t}"
    )
    fe.title(
        _get_stats_entry_title(range, to_ts - 60)
    )  # minus 1 minute to situate the entry in the right range
    fe.link(href=user_stats_url, rel="alternate")

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


@atom_bp.get("/playlist/<playlist_mbid>")
@crossdomain
@api_listenstore_needed
@ratelimit()
def get_playlist_recordings(playlist_mbid):
    """
    Get recording feed for a playlist.

    :statuscode 200: The feed was successfully generated.
    :statuscode 400: Bad Request.
    :statuscode 401: Invalid authentication.
    :statuscode 404: Playlist not found
    :resheader Content-Type: *application/atom+xml*
    """
    if not is_valid_uuid(playlist_mbid):
        return BadRequest("Invalid playlist MBID")

    playlist = db_playlist.get_by_mbid(db_conn, ts_conn, playlist_mbid, True)

    if playlist is None:
        return NotFound("Playlist not found")

    if not playlist.is_visible_by(None):
        return NotFound("Playlist not found")

    fetch_playlist_recording_metadata(playlist)

    this_feed_url = _external_url_for(".get_playlist_recordings", playlist_mbid=playlist_mbid)
    playlist_page_url = _external_url_for("playlist.playlist_page", path=playlist_mbid)

    fg = _init_feed(
        this_feed_url,
        playlist.name + " - ListenBrainz",
        playlist_page_url,
        this_feed_url,
    )

    for recording in playlist.recordings:
        fe = fg.add_entry()
        fe.id(
            f"{this_feed_url}/{recording.mbid}"
        )
        fe.title(
            f"{recording.title} by {recording.artist_credit} was added to {playlist.name}"
            if recording.artist_credit
            else f"{recording.title} was added to {playlist.name}"
        )
        fe.link(href=playlist_page_url, rel="alternate")

        content = render_template(
            "atom/recording.html",
            recording_mbid=recording.mbid,
            recording_title=recording.title,
            artist_credit=recording.artist_credit,
            artist_mbid=recording.artist_mbids[0] if recording.artist_mbids else None,
            recording_mb_page_base_url="https://musicbrainz.org/recording/",
            artist_page_base_url=_external_url_for(
                "artist.artist_page", path=""),
        )
        fe.content(
            content=content,
            type="html",
        )

        t_with_tz = recording.created.astimezone(timezone.utc)
        fe.published(t_with_tz)
        fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.get("/user/<user_name>/recommendations")
@crossdomain
@api_listenstore_needed
@ratelimit()
def get_recommendation(user_name):
    """
    Get recommendation for a user.

    :param recommendation_type: Type of recommendation to get. See `RECOMMENDATION_TYPES` for possible values.
    :statuscode 200: The feed was successfully generated.
    :statuscode 204: Recommendation for the user haven't been generated.
    :statuscode 400: Bad Request.
    :statuscode 401: Invalid authentication.
    :statuscode 404: Playlist not found
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        return NotFound("User not found")

    recommendation_type = request.args.get(
        "recommendation_type", default=RECOMMENDATION_TYPES[0]
    )
    if recommendation_type not in RECOMMENDATION_TYPES:
        return BadRequest("Invalid type")

    playlists = db_playlist.get_recommendation_playlists_for_user(
        db_conn, ts_conn, user["id"]
    )

    playlist = next(
        (
            pl
            for pl in playlists
            if pl.additional_metadata.get("algorithm_metadata", {}).get(
                "source_patch", None
            )
            == recommendation_type
        ),
        None,
    )

    if playlist is None:
        return Response(
            status=204, response="Recommedation for the user haven't been generated."
        )
        
    playlist = db_playlist.get_by_mbid(db_conn, ts_conn, playlist.mbid, True)

    fetch_playlist_recording_metadata(playlist)

    this_feed_url = f"{_external_url_for('.get_recommendation', user_name=user_name)}/{recommendation_type}"
    playlist_page_url = _external_url_for("playlist.playlist_page", path=playlist.mbid)

    recommendation_type_titlecase = recommendation_type.title().replace("-"," ")

    fg = _init_feed(
        this_feed_url,
        f"{recommendation_type_titlecase} for {user_name} - ListenBrainz",
        this_feed_url,
        playlist_page_url,
    )

    fe = fg.add_entry()
    fe.id(
        f"{this_feed_url}/{playlist.created.timestamp()}"
    )
    fe.title(playlist.name)
    fe.link(href=playlist_page_url, rel="alternate")

    content = render_template(
        "atom/playlist.html",
        tracks=playlist.recordings,
        recording_mb_page_base_url="https://musicbrainz.org/recording/",
        artist_page_base_url=_external_url_for("artist.artist_page", path=""),
    )
    fe.content(
        content=content,
        type="html",
    )

    t_with_tz = playlist.created.astimezone(timezone.utc)
    fe.published(t_with_tz)
    fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.get("/user/<user_name>/stats/art/grid")
@crossdomain
@ratelimit()
def get_cover_art_grid_stats(user_name):
    """
    Get cover art grid stats for a user.
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``month``
    :type range: ``str``
    :param dimension: Optional, dimension of the grid, defaults to 4
    :type dimension: ``int``
    :param layout: Optional, layout of the grid, defaults to 0
    :type layout: ``int``
    :param image_size: Optional, size of the image, defaults to 750
    :type image_size: ``int``
    :statuscode 200: The feed was successfully generated.
    :statuscode 204: Statistics for the user haven't been calculated.
    :statuscode 400: Bad request
    :statuscode 404: User not found
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise NotFound("User not found")

    range = request.args.get("range", default="month")
    if not _is_valid_range(range):
        return BadRequest(f"Invalid range value: {range}")

    try:
        dimension = int(request.args.get("dimension", 4))
        layout = int(request.args.get("layout", 0))
        image_size = int(request.args.get("image_size", 750))
    except ValueError:
        return BadRequest("Dimension, layout, and image_size must be integers.")

    if not (MIN_DIMENSION <= dimension <= MAX_DIMENSION):
        return BadRequest(
            f"Dimension must be between {MIN_DIMENSION} and {MAX_DIMENSION}."
        )

    if not (MIN_IMAGE_SIZE <= image_size <= MAX_IMAGE_SIZE):
        return BadRequest(
            f"Image size must be between {MIN_IMAGE_SIZE} and {MAX_IMAGE_SIZE}."
        )

    # Generate the data URL for the art
    # Using API_URL + API_PREFIX otherwise we link to lb.org/1/art/...
    # which returns an error message to use api.lb.org/1/art/...
    data_url = f'{current_app.config["API_URL"]}{API_PREFIX}/art/grid-stats/{user_name}/{range}/{dimension}/{layout}/{image_size}'

    this_feed_url = _external_url_for(".get_cover_art_grid_stats", user_name=user_name, range=range)
    user_stats_url = _external_url_for("user.index", path="stats", user_name=user_name, range=range)

    fg = _init_feed(
        this_feed_url,
        _get_cover_art_feed_title(user_name, range, art_type="grid"),
        user_stats_url,
        this_feed_url,
    )

    entity_list, to_ts, last_updated = _get_entity_stats(
        user["id"],
        "releases",
        range,
        1,  # Fetch a single stat to get last_updated
    )
    if entity_list is None:
        return Response(
            status=204, response="Statistics for the user haven't been calculated."
        )

    if _is_daily_updated_stats(range):
        t = last_updated
    else:
        t = to_ts
    dt = datetime.fromtimestamp(t)
    t_with_tz = dt.replace(tzinfo=timezone.utc)

    fe = fg.add_entry()
    fe.id(
        f"{this_feed_url}/{t}"
    )
    fe.title(_get_stats_entry_title(range, to_ts - 60) + " (Stats Art Grid)")
    fe.link(href=data_url, rel="alternate")

    cover_art_api_response = cover_art_grid_stats(
        user_name=user_name,
        time_range=range,
        dimension=dimension,
        layout=layout,
        image_size=image_size,
    )
    rendered_svg =  cover_art_api_response.get_data()

    fe.content(content=rendered_svg, type="image/svg+xml")
    fe.published(t_with_tz)
    fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)
    return Response(atomfeed, mimetype="application/atom+xml")


@atom_bp.get("/user/<user_name>/stats/art/custom")
@crossdomain
@ratelimit()
def get_cover_art_custom_stats(user_name):
    """
    Get custom cover art stats for a user.
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``month``
    :param custom_name: Optional, name of the custom art, defaults to ``designer-top-5``
    :type custom_name: ``str``
    :type range: ``str``
    :param image_size: Optional, size of the image, defaults to 750
    :type image_size: ``int``
    :statuscode 200: The feed was successfully generated.
    :statuscode 204: Statistics for the user haven't been calculated.
    :statuscode 400: Bad request
    :statuscode 404: User not found
    :resheader Content-Type: *application/atom+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise NotFound("User not found")

    range = request.args.get("range", default="month")
    if not _is_valid_range(range):
        return BadRequest(f"Invalid range value: {range}")

    try:
        custom_name = request.args.get("custome_name", "designer-top-5")
        image_size = int(request.args.get("image_size", 750))
    except ValueError:
        return BadRequest("Image size must be an integer.")

    if custom_name not in ["designer-top-5", "designer-top-10", "lps-on-the-floor"]:
        return BadRequest(f"Invalid custom name: {custom_name}")

    if not (MIN_IMAGE_SIZE <= image_size <= MAX_IMAGE_SIZE):
        return BadRequest(
            f"Image size must be between {MIN_IMAGE_SIZE} and {MAX_IMAGE_SIZE}."
        )

    # Generate the data URL for the art
    # Using API_URL + API_PREFIX otherwise we link to lb.org/1/art/...
    # which returns an error message to use api.lb.org/1/art/...
    data_url = f'{current_app.config["API_URL"]}{API_PREFIX}/art/{custom_name}/{user_name}/{range}/{image_size}'

    this_feed_url = _external_url_for(".get_cover_art_custom_stats", user_name=user_name, range=range)
    user_stats_url = _external_url_for("user.index", path="stats", user_name=user_name, range=range)
    
    fg = _init_feed(
        this_feed_url,
        _get_cover_art_feed_title(
            user_name, range, art_type="custom", custom_name=custom_name
        ),
        user_stats_url,
        this_feed_url,
    )

    if custom_name == "designer-top-5":
        entity_list, to_ts, last_updated = _get_entity_stats(
            user["id"],
            "artists",
            range,
            1,
        )
    else:
        entity_list, to_ts, last_updated = _get_entity_stats(
            user["id"],
            "releases",
            range,
            1,
        )
    if entity_list is None:
        return Response(
            status=204, response="Statistics for the user haven't been calculated."
        )

    if _is_daily_updated_stats(range):
        t = last_updated
    else:
        t = to_ts
    dt = datetime.fromtimestamp(t)
    t_with_tz = dt.replace(tzinfo=timezone.utc)

    fe = fg.add_entry()
    fe.id(
        f"{this_feed_url}/{t}"
    )
    fe.title(_get_stats_entry_title(range, to_ts - 60))
    fe.link(href=data_url, rel="alternate")

    cover_art_api_response = cover_art_custom_stats(
        custom_name=custom_name,
        user_name=user_name,
        time_range=range,
        image_size=image_size
        )
    rendered_svg =  cover_art_api_response.get_data()

    fe.content(content=rendered_svg, type="image/svg+xml")
    fe.published(t_with_tz)
    fe.updated(t_with_tz)

    atomfeed = fg.atom_str(pretty=True)
    return Response(atomfeed, mimetype="application/atom+xml")


def _generate_event_title(event):
    if event.event_type == UserTimelineEventType.RECORDING_RECOMMENDATION:
        track_name = event.metadata.track_metadata.track_name
        artist_name = event.metadata.track_metadata.artist_name
        return f"{event.user_name} recommended {track_name} by {artist_name}"

    elif event.event_type == UserTimelineEventType.FOLLOW:
        followed_user = event.metadata.user_name_1
        return f"{event.user_name} started following {followed_user}"

    elif event.event_type == UserTimelineEventType.LISTEN:
        track_name = event.metadata.track_metadata.track_name
        artist_name = event.metadata.track_metadata.artist_name
        return f"{event.user_name} listened to {track_name} by {artist_name}"

    elif event.event_type == UserTimelineEventType.NOTIFICATION:
        return f"Notification!"

    elif event.event_type == UserTimelineEventType.RECORDING_PIN:
        track_name = event.metadata.track_metadata.track_name
        artist_name = event.metadata.track_metadata.artist_name
        return f"{event.user_name} pinned {track_name} by {artist_name}"

    elif event.event_type == UserTimelineEventType.CRITIQUEBRAINZ_REVIEW:
        entity_name = event.metadata.entity_name
        return f"{event.user_name} reviewed {entity_name} on CritiqueBrainz"

    elif event.event_type == UserTimelineEventType.PERSONAL_RECORDING_RECOMMENDATION:
        track_name = event.metadata.track_metadata.track_name
        artist_name = event.metadata.track_metadata.artist_name
        return f"{event.user_name} recommended {track_name} by {artist_name} to friends"

    else:
        return f"Event for {event.user_name}"


# Commented out as new OAuth is not merged yet. Once merged, update this function to use the new OAuth API to 
# authenticate the user and then fetch the user's events feed.
# @atom_bp.get("/user/<user_name>/events")
# @crossdomain
# @ratelimit()
# @api_listenstore_needed
# def get_user_events(user_name):
#     """
#     Get events feed for a user.

#     :param minutes: The time interval in minutes from current time to fetch events for.
#                     Default is 60 minutes.
#     :statuscode 200: The feed was successfully generated.
#     :statuscode 404: User not found.
#     :resheader Content-Type: *application/atom+xml*
#     """
#     user = db_user.get_by_mb_id(db_conn, user_name)
#     if user is None:
#         return NotFound("User not found")

#     minutes = request.args.get("minutes", DEFAULT_MINUTES_OF_EVENTS, type=int)

#     if minutes < 1 or minutes > 10080:
#         return BadRequest("Value of minutes is out of range")

#     to_ts = datetime.now()
#     from_ts = to_ts - timedelta(minutes=minutes)

#     users_following = db_user_relationship.get_following_for_user(
#         db_conn, user["id"])

#     user_events = get_feed_events_for_user(
#         user=user,
#         followed_users=users_following,
#         min_ts=int(from_ts.timestamp()),
#         max_ts=int(to_ts.timestamp()),
#         count=MAX_ITEMS_PER_GET,
#     )

#     fg = _init_feed(
#         _external_url_for(".get_user_events", user_name=user_name),
#         f"Feeds for {user_name} - ListenBrainz",
#         _external_url_for("user.index", path="", user_name=user_name),
#         _external_url_for(".get_user_events", user_name=user_name),
#     )

#     user_page_url = _external_url_for("user.index", user_name=user_name)
#     user_page_base_url = _external_url_for("user.index", user_name="")[:-1]
#     artist_page_base_url = _external_url_for("artist.artist_page", path="")
#     recording_mb_page_base_url = "https://musicbrainz.org/recording/"

#     for event in user_events:
#         current_app.logger.debug(f"Event: {event}")
#         fe = fg.add_entry()
#         fe.id(
#             f"{_external_url_for('.get_user_events', user_name=user_name)}/{event.created}/{event.id}"
#         )

#         title = _generate_event_title(event)
#         fe.title(title)

#         if event.event_type == UserTimelineEventType.RECORDING_RECOMMENDATION:
#             template_name = "atom/recording_recommendation_event.html"
#         elif event.event_type == UserTimelineEventType.FOLLOW:
#             template_name = "atom/follow_event.html"
#         elif event.event_type == UserTimelineEventType.LISTEN:
#             template_name = "atom/listen_event.html"
#         elif event.event_type == UserTimelineEventType.NOTIFICATION:
#             template_name = "atom/notification_event.html"
#         elif event.event_type == UserTimelineEventType.RECORDING_PIN:
#             template_name = "atom/recording_pin_event.html"
#         elif event.event_type == UserTimelineEventType.CRITIQUEBRAINZ_REVIEW:
#             template_name = "atom/cb_review_event.html"
#         elif (
#             event.event_type == UserTimelineEventType.PERSONAL_RECORDING_RECOMMENDATION
#         ):
#             template_name = "atom/personal_recommendation_event.html"
#         else:
#             assert False, f"Invalid event type: {event.event_type}"

#         content = render_template(
#             template_name,
#             event=event,
#             user_page_url=user_page_url,
#             user_page_base_url=user_page_base_url,
#             artist_page_base_url=artist_page_base_url,
#             recording_mb_page_base_url=recording_mb_page_base_url,
#         )
#         fe.content(content=content, type="html")
#         fe.published(datetime.fromtimestamp(event.created, tz=timezone.utc))
#         fe.updated(datetime.fromtimestamp(event.created, tz=timezone.utc))

#     atomfeed = fg.atom_str(pretty=True)
#     return Response(atomfeed, mimetype="application/atom+xml")
