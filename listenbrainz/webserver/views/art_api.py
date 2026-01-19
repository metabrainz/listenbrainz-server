from itertools import cycle

from markupsafe import Markup

import listenbrainz.db.user as db_user
import listenbrainz.db.year_in_music as db_yim
import listenbrainz.db.playlist as db_playlist

from brainzutils.ratelimit import ratelimit
from flask import request, render_template, Blueprint, current_app

from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APINotFound
from listenbrainz.webserver.views.api_tools import is_valid_uuid, _parse_bool_arg, validate_auth_header
from listenbrainz.webserver.views.playlist_api import PLAYLIST_TRACK_EXTENSION_URI, fetch_playlist_recording_metadata
from listenbrainz.webserver.views.playlist import get_cover_art_options
from listenbrainz.webserver.views.legacy_year_in_music_api import cover_art_yim_legacy

art_api_bp = Blueprint('art_api_v1', __name__)


def _repeat_images(images, size=9):
    """ Repeat the images so that we have required number of images. """
    if len(images) >= size:
        return images
    repeater = cycle(images)
    while len(images) < size:
        images.append(next(repeater))
    return images


@art_api_bp.post("/grid/")
@crossdomain
@ratelimit()
def cover_art_grid_post():
    """
    Create a cover art grid SVG file from the POSTed JSON data to this endpoint. The JSON data
    should look like the following:

    .. literalinclude:: ../../../listenbrainz/art/misc/sample_cover_art_grid_post_request.json
       :language: json

    :param background: The background for the cover art: Must be "transparent", "white" or "black".
    :type background: ``str``
    :param image_size: The size of the cover art image. See constants at the bottom of this document.
    :type image_size: ``int``
    :param dimension: The dimension to use for this grid. A grid of dimension 3 has 3 images across
                      and 3 images down, for a total of 9 images.
    :type dimension: ``int``
    :param skip-missing: If cover art is missing for a given release_mbid, skip it and move on to the next
                         one, if true is passed. If false, the show-caa option will decide what happens.
    :type skip-missing: ``bool``
    :param show-caa: If cover art is missing and skip-missing is false, then show-caa will determine if
                     a blank square is shown or if the Cover Art Archive missing image is show.
                         one, if true is passed. If false, the show-caa option will decide what happens.
    :type show-caa: ``bool``
    :param caption: Whether to show the release name and artist overlayed on each cover art image. Default True.
    :type caption: ``boolean``
    :param tiles: The tiles paramater is a list of strings that determines the location where cover art
                  images should be placed. Each string is a comma separated list of image cells. A grid of
                  dimension 3 has 9 cells, from 0 in the upper left hand corner, 2 in the upper right
                  hand corner, 6 in the lower left corner and 8 in the lower right corner. Specifying
                  only a single cell will have the image cover that cell exactly. If more than one
                  cell is specified, the image will cover the area defined by the bounding box of all
                  the given cells. These tiles only define bounding box areas -- no clipping of images
                  that may fall outside of these tiles will be performed.
    :type tiles: ``list``
    :param release_mbids: An ordered list of release_mbids. The images will be loaded and processed
                          in the order that this list is in. The cover art for the release_mbids will be placed
                          on the tiles defined by the tiles parameter. If release_group_mbids are supplied as well,
                          ONLY cover arts for release_group_mbids will be processed.
    :type release_mbids: ``list``
    :param release_group_mbids: An ordered list of release_group_mbids. The images will be loaded and processed
                          in the order that this list is in. The cover art for the release_group_mbids will be placed
                          on the tiles defined by the tiles parameter. If release_mbids are supplied as well, ONLY cover arts
                          for release_mbids will be processed.
    :type release_group_mbids: ``list``
    :param cover_art_size: Size in pixels of each cover art in the composited image. Can be either 250 or 500
    :type cover_art_size: ``int``

    :statuscode 200: cover art created successfully.
    :statuscode 400: Invalid JSON or invalid options in JSON passed. See error message for details.
    :resheader Content-Type: *image/svg+xml*

    See the bottom of this document for constants relating to this method.
    """

    r = request.json

    if "tiles" in r:
        tiles = r["tiles"]
    else:
        tiles = None

    if "layout" in r:
        layout = r["layout"]
    else:
        layout = None

    show_caption = r.get("caption", True)

    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"],
        r.get("dimension"),
        r.get("image_size"),
        r.get("background"),
        r.get("skip-missing"),
        r.get("show-caa"),
        show_caption=show_caption,
        server_root_url=current_app.config["SERVER_ROOT_URL"],
    )

    err = cac.validate_parameters()
    if err is not None:
        raise APIBadRequest(err)

    if "cover_art_size" in r:
        cover_art_size = r["cover_art_size"]
    elif r["image_size"] < 1000:
        cover_art_size = 250
    else:
        cover_art_size = 500

    # Get release_mbids or release_group_mbids
    mbids = []
    entity = "release"

    def get_release_group_mbids() -> tuple[list, str]:
        """
        Sanity checks and gets `release_group_mbids` in response.
        """
        if "release_group_mbids" not in r:
            return

        if not isinstance(r["release_group_mbids"], list):
            raise APIBadRequest("release_group_mbids must be a list of strings specifying release_group_mbids")

        mbids = list(r["release_group_mbids"])
        entity = "release_group"

        return mbids, entity

    if "release_mbids" in r:
        if not isinstance(r["release_mbids"], list):
            raise APIBadRequest("release_mbids must be a list of strings specifying release_mbids")

        mbids = list(r["release_mbids"])

        # release mbids list empty? Fallback to release group mbids.
        if (len(r["release_mbids"]) == 0):
            mbids, entity = get_release_group_mbids()
    else:
        mbids, entity = get_release_group_mbids()

    if len(mbids) > 100:
        mbids = mbids[:100]

    # Validate mbids
    for mbid in mbids:
        if not is_valid_uuid(mbid):
            raise APIBadRequest(f"Invalid release_mbid {mbid} specified.")

    images = cac.load_images(release_mbids=mbids if entity == "release" else [],
                             release_group_mbids=mbids if entity == "release_group" else [],
                             tile_addrs=tiles,
                             layout=layout,
                             cover_art_size=cover_art_size)
    if images is None:
        raise APIInternalServerError("Failed to grid cover art SVG")

    return render_template("art/svg-templates/simple-grid.svg",
                           background=r["background"],
                           images=images,
                           entity=entity,
                           width=r["image_size"],
                           height=r["image_size"],
                           show_caption=show_caption), 200, {
                               'Content-Type': 'image/svg+xml'
                           }


@art_api_bp.get("/grid-stats/<mb_username:user_name>/<time_range>/<int:dimension>/<int:layout>/<int:image_size>")
@crossdomain
@ratelimit()
def cover_art_grid_stats(user_name, time_range, dimension, layout, image_size):
    """
    Create a cover art grid SVG file from the stats of a given user.

    :param user_name: The name of the user for whom to create the cover art.
    :type user_name: ``str``
    :param time_range: Must be a statistics time range -- see below.
    :type time_range: ``str``
    :param dimension: The dimension to use for this grid. A grid of dimension 3 has 3 images across
                      and 3 images down, for a total of 9 images.
    :type dimension: ``int``
    :param layout: The layout to be used for this grid. Layout 0 is always a simple grid, but other layouts
                   may have image images be of different sizes. See https://art.listenbrainz.org for examples
                   of the available layouts.
    :type layout: ``int``
    :param image_size: The size of the cover art image. See constants at the bottom of this document.
    :type image_size: ``int``
    :param caption: Whether to show the release name and artist overlayed on each cover art image. Default True
    :type caption: ``boolean``
    :param skip-missing: Whether to skip albums that don't have cover art, or show a placeholder. Default True
    :type skip-missing: ``boolean``
    :statuscode 200: cover art created successfully.
    :statuscode 400: Invalid JSON or invalid options in JSON passed. See error message for details.
    :resheader Content-Type: *image/svg+xml*

    See the bottom of this document for constants relating to this method.
    """
    show_caption = _parse_bool_arg("caption", True)
    skip_missing = _parse_bool_arg("skip-missing", True)
    
    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], dimension, image_size, show_caption=show_caption, skip_missing=skip_missing,
        server_root_url=current_app.config["SERVER_ROOT_URL"])
    err = cac.validate_parameters()
    if err is not None:
        raise APIBadRequest(err)

    try:
        _ = cac.GRID_TILE_DESIGNS[dimension][layout]
    except IndexError:
        return f"layout {layout} is not available for dimension {dimension}."

    try:
        images, eng_time_range = cac.create_grid_stats_cover(user_name, time_range, layout)
        if images is None:
            raise APIInternalServerError("Failed to grid cover art SVG")
    except ValueError as error:
        raise APIBadRequest(str(error))

    title = f"Top {len(images)} Releases {eng_time_range} for {user_name} \n"
    desc = ""
    for i in range(len(images)):
        desc += f"{i+1}. {images[i]['title']} - {images[i]['artist']} \n"

    return render_template("art/svg-templates/simple-grid.svg",
                           background=cac.background,
                           images=images,
                           title=title,
                           desc=desc,
                           entity="release",
                           width=image_size,
                           height=image_size,
                           show_caption=show_caption), 200, {
                               'Content-Type': 'image/svg+xml'
                           }


@art_api_bp.get("/<custom_name>/<mb_username:user_name>/<time_range>/<int:image_size>")
@crossdomain
@ratelimit()
def cover_art_custom_stats(custom_name, user_name, time_range, image_size):
    """
    Create a custom cover art SVG file from the stats of a given user.

    :param cover_name: The name of cover art to be generated. See https://art.listenbrainz.org for the different types
                       that are available.
    :type cover_name: ``str``
    :param user_name: The name of the user for whom to create the cover art.
    :type user_name: ``str``
    :param time_range: Must be a statistics time range -- see below.
    :type time_range: ``str``
    :param image_size: The size of the cover art image. See constants at the bottom of this document.
    :type image_size: ``int``
    :statuscode 200: cover art created successfully.
    :statuscode 400: Invalid JSON or invalid options in JSON passed. See error message for details.
    :resheader Content-Type: *image/svg+xml*

    See the bottom of this document for constants relating to this method.

    """

    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], 3, image_size,
        server_root_url=current_app.config["SERVER_ROOT_URL"])
    err = cac.validate_parameters()
    if err is not None:
        raise APIBadRequest(err)

    if custom_name in ("designer-top-5",):
        try:
            artists, metadata = cac.create_artist_stats_cover(user_name, time_range)
            if artists is None:
                raise APIInternalServerError("Failed to artist cover art SVG")
        except ValueError as error:
            raise APIBadRequest(str(error))

        return render_template(f"art/svg-templates/{custom_name}.svg",
                               artists=artists,
                               width=image_size,
                               height=image_size,
                               metadata=metadata), 200, {
                                   'Content-Type': 'image/svg+xml'
                               }

    if custom_name in ("lps-on-the-floor", "designer-top-10", "designer-top-10-alt"):
        try:
            images, releases, metadata = cac.create_release_stats_cover(user_name, time_range)
            if images is None:
                raise APIInternalServerError("Failed to release cover art SVG")
            if custom_name == "lps-on-the-floor":
                images = _repeat_images(images, 5)
        except ValueError as error:
            raise APIBadRequest(str(error))

        cover_art_on_floor_url = f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/cover-art-on-floor.png'
        return render_template(f"art/svg-templates/{custom_name}.svg",
                               cover_art_on_floor_url=cover_art_on_floor_url,
                               images=images,
                               releases=releases,
                               width=image_size,
                               height=image_size,
                               metadata=metadata), 200, {
                                   'Content-Type': 'image/svg+xml'
                               }

    raise APIBadRequest(f"Unkown custom cover art type {custom_name}")


def _cover_art_yim_stats(user_name, stats, year, options, styles):
    """ Create the SVG using YIM statistics for the given year. """
    if stats.get("day_of_week") is None or stats.get("most_listened_year") is None or \
        stats.get("total_listen_count") is None or stats.get("total_new_artists_discovered") is None or \
            stats.get("total_artists_count") is None:
        return None

    match stats["day_of_week"]:
        case "Monday": most_played_day_message = 'I SURVIVED <tspan class="user-stat">MONDAYS</tspan> WITH MUSIC'
        case "Tuesday": most_played_day_message = 'I CHILLED WITH MUSIC ON <tspan class="user-stat">TUESDAY</tspan>'
        case "Wednesday": most_played_day_message = 'I GOT THROUGH <tspan class="user-stat">WEDNESDAYS</tspan> WITH MUSIC'
        case "Thursday": most_played_day_message = 'I SPENT TIME WITH MY TUNES ON <tspan class="user-stat">THURSDAYS</tspan>'
        case "Friday": most_played_day_message = 'I CELEBRATED <tspan class="user-stat">FRIDAYS</tspan> WITH MUSIC'
        case "Saturday": most_played_day_message = 'I PARTIED HARD (OR HARDLY!) ON <tspan class="user-stat">SATURDAYS</tspan>'
        case "Sunday": most_played_day_message = 'I LOVED SPENDING <tspan class="user-stat">SUNDAYS</tspan> WITH MUSIC'
        case other: most_played_day_message = f'I CRANKED TUNES ON <tspan class="user-stat">{other}</tspan>'

    most_listened_year = max(stats["most_listened_year"], key=stats["most_listened_year"].get)


    return render_template(
        "art/svg-templates/year-in-music/yim-stats.svg",
        user_name=user_name,
        most_played_day_message=Markup(most_played_day_message),
        most_listened_year=most_listened_year,
        total_listen_count=stats["total_listen_count"],
        total_new_artists_discovered=stats["total_new_artists_discovered"],
        total_artists_count=stats["total_artists_count"],
        year=year,
        **options,
        **styles,
    )


def _cover_art_yim_albums(user_name, stats, year, options, styles):
    """ Create the SVG using YIM top albums for the given year. """
    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], 3, 750,
        server_root_url=current_app.config["SERVER_ROOT_URL"],
        show_caption=True)
    images = []

    if stats.get("top_release_groups") is None:
        return None

    for release_group in stats["top_release_groups"]:
        if "caa_id" in release_group and "caa_release_mbid" in release_group:
            image = {
                "title": release_group["release_group_name"],
                "artist": release_group["artist_name"],
                "entity_mbid": release_group["release_group_mbid"],
                "caa_id": release_group["caa_id"], 
                "caa_release_mbid": release_group["caa_release_mbid"]
            }
            images.append(image)

    if len(images) == 0:
        return None

    images = _repeat_images(images, size=9)

    # Generate the cover art images
    images = cac.generate_from_caa_ids(
        images, layout=0, cover_art_size=250)

    return render_template(
        "art/svg-templates/year-in-music/yim-albums.svg",
        user_name=user_name,
        images=images,
        year=year,
        **options,
        **styles,
    )


def _cover_art_yim_tracks(user_name, stats, year, options, styles):
    """ Create the SVG using top tracks for the given user. """
    if stats.get("top_recordings") is None:
        return None

    return render_template(
        "art/svg-templates/year-in-music/yim-tracks.svg",
        user_name=user_name,
        tracks=stats["top_recordings"],
        year=year,
        **options,
        **styles,
    )


def _cover_art_yim_artists(user_name, stats, year, options, styles):
    """ Create the SVG using top artists for the given user. """
    if stats.get("top_artists") is None:
        return None

    return render_template(
        "art/svg-templates/year-in-music/yim-artists.svg",
        user_name=user_name,
        artists=stats["top_artists"],
        total_artists_count=stats["total_artists_count"],
        year=year,
        **options,
        **styles,
    )


def _cover_art_yim_playlist(user_name, stats, key, year, options, styles):
    """ Create the SVG using playlist tracks' cover arts for the given YIM playlist. """
    if stats.get(key) is None:
        return None

    images = []
    selected_urls = set()

    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], dimension=3, image_size=500,
        server_root_url=current_app.config["SERVER_ROOT_URL"])

    for track in stats[key]["track"]:
        additional_metadata = track["extension"][PLAYLIST_TRACK_EXTENSION_URI].get("additional_metadata")
        if additional_metadata.get("caa_id") and additional_metadata.get("caa_release_mbid"):
            caa_id = additional_metadata.get("caa_id")
            caa_release_mbid = additional_metadata.get("caa_release_mbid")
            # check existence in set to avoid duplicates
            if caa_id not in selected_urls:
                images.append({
                    "caa_id": caa_id,
                    "caa_release_mbid": caa_release_mbid,
                    "title": track.get("title"),
                    "entity_mbid": track["identifier"][0].split("/")[-1],
                    "artist": track.get("creator")
                })
                selected_urls.add(caa_id)
    
    if len(images) == 0:
        return None

    images = _repeat_images(images)

    cover_art_images = cac.generate_from_caa_ids(
        images, layout=0, cover_art_size=250)

    if not options.get("branding"):
        # Return a simple grid for use on the YIM page
        return render_template(
            "art/svg-templates/simple-grid.svg",
            background="transparent",
            images=cover_art_images,
            title=stats[key].get("title"),
            desc=stats[key].get("annotation"),
            entity="track",
            width=500,
            height=500,
            **options,
            **styles,
        )

    match key:
        case "playlist-top-discoveries-for-year":
            target_svg = "art/svg-templates/year-in-music/yim-discovery-playlist.svg"
        case "playlist-top-missed-recordings-for-year":
            target_svg = "art/svg-templates/year-in-music/yim-missed-tracks-playlist.svg"
        case other:
            raise APIBadRequest(f"Invalid playlist type {key}. Playlist type should be one of (playlist-top-discoveries-for-year, playlist-top-missed-recordings-for-year)")

    return render_template(
        target_svg,
        user_name=user_name,
        images=cover_art_images,
        year=year,
        width=924,
        height=924,
        entity="track",
        **options,
        **styles,
    )


def _cover_art_yim_overview(user_name, stats, year, options, styles):
    """ Create the SVG using top stats for the overview YIM image. """
    filtered_genres = []
    total_filtered_genre_count = 0
    number_of_genres =  6
    for genre in stats.get("top_genres", []):
        # In 2023 we filtered out the most popular genres
        if year > 2023 or genre["genre"] not in ("pop", "rock", "electronic", "hip hop"):
            filtered_genres.append(genre)
            total_filtered_genre_count += genre["genre_count"]

    filtered_top_genres = []
    for genre in filtered_genres[:number_of_genres]:
        genre_count_percent = round(genre["genre_count"] / total_filtered_genre_count * 100)
        filtered_top_genres.append({"genre": genre["genre"], "genre_count_percent": genre_count_percent})

    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], 3, 250,
        server_root_url=current_app.config["SERVER_ROOT_URL"])

    albums = []
    for release_group in stats.get("top_release_groups", [])[:2]:
        if release_group.get("caa_id") and release_group.get("caa_release_mbid"):
            cover_art = cac.resolve_cover_art(release_group["caa_id"], release_group["caa_release_mbid"], 250)
        else:
            cover_art = None
        albums.append({
            "artist": release_group["artist_name"],
            "title": release_group["release_group_name"],
            "listen_count": release_group["listen_count"],
            "cover_art": cover_art
        })

    if len(albums) == 2:
        album_1, album_2 = albums[0], albums[1]
    elif len(albums) == 1:
        album_1, album_2 = albums[0], None
    else:
        album_1, album_2 = None, None

    props = {
        "artists_count": stats.get("total_artists_count", 0),
        "albums_count": stats.get("total_release_groups_count", 0),
        "songs_count": stats.get("total_recordings_count", 0),
        "genres": filtered_top_genres,
        "user_name": user_name,
        "album_1": album_1,
        "album_2": album_2,
        "year":year,
    }

    return render_template("art/svg-templates/year-in-music/yim-overview.svg", **props, **options, **styles)


@art_api_bp.get("/year-in-music/<int:year>/<mb_username:user_name>")
@crossdomain
@ratelimit()
def cover_art_yim(user_name, year: int = 2025):
    """ Create shareable SVG images using Year In Music stats
    
    :param year: The selected year for which to create the Year In Music cover art.
    :type year: ``int``
    :param user_name: The name of the user for whom to create the cover art.
    :type user_name: ``str``
    :param branding: Show or hide the LsitenBrainz branding on the image. Default True.
    :type branding: ``bool``
    :param show-caption: For cover art grids, show or hide the album title and artist name. Default True.
    :type show-caption: ``bool``
    :param anonymous: Show or hide the user's name. Default False (shows user name).
    :type anonymous: ``bool``
    :param bg-color-1: Background color 1 to use in the image. Default #2f6368.
    :type bg-color-1: ``str``
    :param bg-color-2: Background color 2 to use in the image. Default #463f62.
    :type bg-color-2: ``str``
    :param accent-color: Accent color to use in the image. Default #F1F2E1.
    :type accent-color: ``str``
    :param legacy: Generate images from archived previous versions of YIM. Deprecated. Default False.
    :type legacy: ``bool``
    :statuscode 200: Image created successfully.
    :statuscode 204: Missing enough data to generate an image for the selected year and user.
    :statuscode 400: Invalid JSON or invalid options in JSON passed. See error message for details.
    :resheader Content-Type: *image/svg+xml*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APIBadRequest(f"User {user_name} not found")

    image = request.args.get("image")
    if image is None:
        raise APIBadRequest(
            "Type of Image needs to be specified should be one of (overview, stats, artists, albums, tracks, discovery-playlist, missed-playlist)")

    branding = _parse_bool_arg("branding", True)
    legacy = _parse_bool_arg("legacy", False)
    show_caption = _parse_bool_arg("show-caption", True)
    anonymous = _parse_bool_arg("anonymous", False)

    if legacy:
        if year < 2021 or year > 2024:
            raise APIBadRequest("Legacy Year In Music images are only available for years 2021, 2022, 2023 and 2024")
        return cover_art_yim_legacy(user=user, year=year, image=image, branding=branding)

    stats = db_yim.get(user["id"], year, legacy=False)
    if stats is None:
        raise APIBadRequest(f"Year In Music {year} report for user {user_name} not found")

    options = {
        "anonymous": anonymous,
        "branding": branding,
        "show_caption": show_caption
    }
    styles = {
        "background_color_1": request.args.get("bg-color-1", "#2f6368"),
        "background_color_2": request.args.get("bg-color-2", "#463f62"),
        "accent_color": request.args.get("accent-color", "#F1F2E1"),
    }

    match image:
        case "overview": svg = _cover_art_yim_overview(user_name, stats, year, options, styles)
        case "stats": svg = _cover_art_yim_stats(user_name, stats, year, options, styles)
        case "albums": svg = _cover_art_yim_albums(user_name, stats, year, options, styles)
        case "tracks": svg = _cover_art_yim_tracks(user_name, stats, year, options, styles)
        case "artists": svg = _cover_art_yim_artists(user_name, stats, year, options, styles)
        case "discovery-playlist": svg = _cover_art_yim_playlist(user_name, stats, "playlist-top-discoveries-for-year", year, options, styles)
        case "missed-playlist": svg = _cover_art_yim_playlist(user_name, stats, "playlist-top-missed-recordings-for-year", year, options, styles)
        case other: raise APIBadRequest(f"Invalid image type {other}. Image type should be one of (stats, artists, albums, tracks, discovery-playlist, missed-playlist)")

    if svg is None:
        return "", 204

    return svg, 200, {"Content-Type": "image/svg+xml"}


@art_api_bp.post("/playlist/<uuid:playlist_mbid>/<int:dimension>/<int:layout>")
@crossdomain
@ratelimit()
def playlist_cover_art_generate(playlist_mbid, dimension, layout):
    """
    Create a cover art grid SVG file from the playlist.

    :param playlist_mbid: The mbid of the playlist for whom to create the cover art.
    :type playlist_mbid: ``str``
    :param dimension: The dimension to use for this grid. A grid of dimension 3 has 3 images across
                      and 3 images down, for a total of 9 images.
    :type dimension: ``int``
    :param layout: The layout to be used for this grid. Layout 0 is always a simple grid, but other layouts
                   may have image images be of different sizes. See https://art.listenbrainz.org for examples
                   of the available layouts.
    :type layout: ``int``
    :statuscode 200: cover art created successfully.
    :statuscode 400: Invalid JSON or invalid options in JSON passed. See error message for details.
    :resheader Content-Type: *image/svg+xml*

    See the bottom of this document for constants relating to this method.
    """
    user = validate_auth_header()

    try:
        grid_design = CoverArtGenerator.GRID_TILE_DESIGNS[dimension][layout]
    except IndexError:
        raise APIBadRequest(f"layout {layout} is not available for dimension {dimension}.")

    playlist = db_playlist.get_by_mbid(db_conn, ts_conn, playlist_mbid, True)
    if playlist is None or not playlist.is_visible_by(user["id"]):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    # Check if the playlist has enough tracks to fill the grid
    if len(playlist.recordings) < len(grid_design):
        raise APIBadRequest("Playlist is too small to generate cover art")

    # Fetch the metadata for the playlist recordings
    fetch_playlist_recording_metadata(playlist)

    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], dimension, 500, show_caption=False,
        server_root_url=current_app.config["SERVER_ROOT_URL"])
    if (validation_error := cac.validate_parameters()) is not None:
        raise APIBadRequest(validation_error)

    # Get cover art options and repeat images if needed
    images = get_cover_art_options(playlist)
    images = _repeat_images(images, len(grid_design))

    # Generate the cover art images
    cover_art_images = cac.generate_from_caa_ids(images, layout=layout, cover_art_size=500)

    # Get the playlist name and description
    title = playlist.name
    desc = playlist.description
    image_size = 500

    # Render the cover art image template
    return render_template("art/svg-templates/simple-grid.svg",
                           background=cac.background,
                           images=cover_art_images,
                           title=title,
                           desc=desc,
                           entity="release",
                           width=image_size,
                           height=image_size,
                           show_caption=False), 200, {
                               'Content-Type': 'image/svg+xml'
                           }
