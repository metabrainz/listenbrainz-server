from itertools import cycle

from markupsafe import Markup

import listenbrainz.db.year_in_music as db_yim

from flask import request, render_template, Blueprint, current_app

from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.webserver.errors import APIBadRequest
from listenbrainz.webserver.views.playlist_api import PLAYLIST_TRACK_EXTENSION_URI

art_api_bp = Blueprint('art_api_v1', __name__)

def _repeat_images(images, size=9):
    """ Repeat the images so that we have required number of images. """
    if len(images) >= size:
        return images
    repeater = cycle(images)
    while len(images) < size:
        images.append(next(repeater))
    return images

def legacy_cover_art_yim_stats(user_name, stats, year, yim24):
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

    if year == 2022:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2022/yim-2022.svg",
            user_name=user_name,
            most_played_day_message=Markup(most_played_day_message),
            most_listened_year=most_listened_year,
            total_listen_count=stats["total_listen_count"],
            total_new_artists_discovered=stats["total_new_artists_discovered"],
            total_artists_count=stats["total_artists_count"],
            bg_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-bg.png',
            magnify_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-magnify.png',
        )

    if year == 2023:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2023/yim-2023-stats.svg",
            user_name=user_name,
            most_played_day_message=Markup(most_played_day_message),
            most_listened_year=most_listened_year,
            total_listen_count=stats["total_listen_count"],
            total_new_artists_discovered=stats["total_new_artists_discovered"],
            total_artists_count=stats["total_artists_count"],
        )

    if year == 2024:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2024/yim-2024-stats.svg",
            user_name=user_name,
            most_played_day_message=Markup(most_played_day_message),
            most_listened_year=most_listened_year,
            total_listen_count=stats["total_listen_count"],
            total_new_artists_discovered=stats["total_new_artists_discovered"],
            total_artists_count=stats["total_artists_count"],
            **yim24,
        )


def _cover_art_yim_albums_2022(user_name, stats):
    """ Create the SVG using YIM top albums for 2022. """
    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], 3, 250,
        server_root_url=current_app.config["SERVER_ROOT_URL"])
    image_urls = []
    selected_urls = set()

    if stats.get("top_releases") is None:
        return None

    for release in stats["top_releases"]:
        if "caa_id" in release and "caa_release_mbid" in release:
            url = cac.resolve_cover_art(release["caa_id"], release["caa_release_mbid"], 250)
            if url not in selected_urls:
                selected_urls.add(url)
                image_urls.append(url)

    if len(image_urls) == 0:
        return None

    image_urls = _repeat_images(image_urls)

    return render_template(
        "art/svg-templates/year-in-music/legacy/2022/yim-2022-albums.svg",
        user_name=user_name,
        image_urls=image_urls,
        bg_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-bg.png',
        flames_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-flames.png',
    )


def _cover_art_yim_albums_2023(user_name, stats):
    """ Create the SVG using YIM top albums for 2023. """
    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], 3, 250,
        server_root_url=current_app.config["SERVER_ROOT_URL"])
    images = []
    selected_urls = set()

    if stats.get("top_release_groups") is None:
        return None

    for release_group in stats["top_release_groups"]:
        if "caa_id" in release_group and "caa_release_mbid" in release_group:
            url = cac.resolve_cover_art(release_group["caa_id"], release_group["caa_release_mbid"], 250)
            if url not in selected_urls:
                selected_urls.add(url)
                images.append({
                    "url": url,
                    "title": release_group["release_group_name"],
                    "artist": release_group["artist_name"],
                    "entity_mbid": release_group["release_group_mbid"]
                })

    if len(images) == 0:
        return None

    images = _repeat_images(images)

    return render_template(
        "art/svg-templates/year-in-music/legacy/2023/yim-2023-albums.svg",
        user_name=user_name,
        images=images,
    )


def _cover_art_yim_albums_2024(user_name, stats, yim24):
    """ Create the SVG using YIM top albums for 2024. """
    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], 3, 250,
        server_root_url=current_app.config["SERVER_ROOT_URL"])
    images = []
    selected_urls = set()

    if stats.get("top_release_groups") is None:
        return None

    for release_group in stats["top_release_groups"]:
        if "caa_id" in release_group and "caa_release_mbid" in release_group:
            url = cac.resolve_cover_art(release_group["caa_id"], release_group["caa_release_mbid"], 250)
            if url not in selected_urls:
                selected_urls.add(url)
                images.append({
                    "url": url,
                    "title": release_group["release_group_name"],
                    "artist": release_group["artist_name"],
                    "entity_mbid": release_group["release_group_mbid"]
                })

    if len(images) == 0:
        return None

    images = _repeat_images(images)

    return render_template(
        "art/svg-templates/year-in-music/legacy/2024/yim-2024-albums.svg",
        user_name=user_name,
        images=images,
        **yim24,
    )


def legacy_cover_art_yim_albums(user_name, stats, year, yim24):
    """ Create the SVG using YIM top albums for the given year. """
    if year == 2022:
        return _cover_art_yim_albums_2022(user_name, stats)

    if year == 2023:
        return _cover_art_yim_albums_2023(user_name, stats)

    if year == 2024:
        return _cover_art_yim_albums_2024(user_name, stats, yim24)


def legacy_cover_art_yim_tracks(user_name, stats, year, yim24):
    """ Create the SVG using top tracks for the given user. """
    if stats.get("top_recordings") is None:
        return None

    if year == 2022:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2022/yim-2022-tracks.svg",
            user_name=user_name,
            tracks=stats["top_recordings"],
            bg_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-bg.png',
            stereo_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-stereo.png',
        )

    if year == 2023:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2023/yim-2023-tracks.svg",
            user_name=user_name,
            tracks=stats["top_recordings"],
        )

    if year == 2024:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2024/yim-2024-tracks.svg",
            user_name=user_name,
            tracks=stats["top_recordings"],
            **yim24,
        )


def legacy_cover_art_yim_artists(user_name, stats, year, yim24):
    """ Create the SVG using top artists for the given user. """
    if stats.get("top_artists") is None:
        return None

    if year == 2022:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2022/yim-2022-artists.svg",
            user_name=user_name,
            artists=stats["top_artists"],
            total_artists_count=stats["total_artists_count"],
            bg_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-bg.png',
        )

    if year == 2023:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2023/yim-2023-artists.svg",
            user_name=user_name,
            artists=stats["top_artists"],
            total_artists_count=stats["total_artists_count"],
        )

    if year == 2024:
        return render_template(
            "art/svg-templates/year-in-music/legacy/2024/yim-2024-artists.svg",
            user_name=user_name,
            artists=stats["top_artists"],
            total_artists_count=stats["total_artists_count"],
            **yim24,
        )


def _cover_art_yim_playlist_2022(user_name, stats, key):
    """ Create the SVG using playlist tracks' cover arts for the given YIM 2022 playlist. """
    if stats.get(key) is None or stats.get(f"{key}-coverart") is None:
        return None

    all_cover_arts = stats[f"{key}-coverart"]
    image_urls = []
    selected_urls = set()

    for track in stats[key]["track"]:
        mbid = track["identifier"].split("/")[-1]
        # check existence in set to avoid duplicates
        if mbid in all_cover_arts and all_cover_arts[mbid] not in selected_urls:
            image_urls.append(all_cover_arts[mbid])
            selected_urls.add(all_cover_arts[mbid])

    if len(image_urls) == 0:
        return None

    if len(image_urls) < 9:
        repeater = cycle(image_urls)
        # fill up the remaining slots with repeated images
        while len(image_urls) < 9:
            image_urls.append(next(repeater))

    return render_template(
        "art/svg-templates/year-in-music/legacy/2022/yim-2022-playlists.svg",
        user_name=user_name,
        image_urls=image_urls,
        bg_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-bg.png',
        flames_image_url=f'{current_app.config["SERVER_ROOT_URL"]}/static/img/art/yim-2022-shareable-flames.png',
    )


def _cover_art_yim_playlist_2023(user_name, stats, key, branding):
    """ Create the SVG using playlist tracks' cover arts for the given YIM 2023 playlist. """
    if stats.get(key) is None:
        return None

    images = []
    selected_urls = set()

    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], 3, 250,
        server_root_url=current_app.config["SERVER_ROOT_URL"])

    for track in stats[key]["track"]:
        additional_metadata = track["extension"][PLAYLIST_TRACK_EXTENSION_URI].get("additional_metadata")
        if additional_metadata.get("caa_id") and additional_metadata.get("caa_release_mbid"):
            caa_id = additional_metadata["caa_id"]
            caa_release_mbid = additional_metadata["caa_release_mbid"]
            cover_art = cac.resolve_cover_art(caa_id, caa_release_mbid, 250)

            # check existence in set to avoid duplicates
            if cover_art not in selected_urls:
                images.append({
                    "url": cover_art,
                    "entity_mbid": caa_release_mbid,
                    "title": track.get("album"),
                    "artist": track.get("creator"),
                })

    if len(images) == 0:
        return None

    images = _repeat_images(images)

    match key:
        case "playlist-top-discoveries-for-year":
            target_svg = "art/svg-templates/year-in-music/legacy/2023/yim-2023-playlist-hug.svg"
        case "playlist-top-missed-recordings-for-year":
            target_svg = "art/svg-templates/year-in-music/legacy/2023/yim-2023-playlist-arrows.svg"
        case other:
            raise APIBadRequest(f"Invalid playlist type {key}. Playlist type should be one of (playlist-top-discoveries-for-year, playlist-top-missed-recordings-for-year)")

    return render_template(
        target_svg,
        user_name=user_name,
        images=images,
        branding=branding
    )


def _cover_art_yim_playlist_2024(user_name, stats, key, branding, yim24):
    """ Create the SVG using playlist tracks' cover arts for the given YIM 2024 playlist. """
    if stats.get(key) is None:
        return None

    images = []
    selected_urls = set()

    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"], 3, 250,
        server_root_url=current_app.config["SERVER_ROOT_URL"])

    for track in stats[key]["track"]:
        additional_metadata = track["extension"][PLAYLIST_TRACK_EXTENSION_URI].get("additional_metadata")
        if additional_metadata.get("caa_id") and additional_metadata.get("caa_release_mbid"):
            caa_id = additional_metadata["caa_id"]
            caa_release_mbid = additional_metadata["caa_release_mbid"]
            cover_art = cac.resolve_cover_art(caa_id, caa_release_mbid, 250)

            # check existence in set to avoid duplicates
            if cover_art not in selected_urls:
                images.append({
                    "url": cover_art,
                    "entity_mbid": caa_release_mbid,
                    "title": track.get("album"),
                    "artist": track.get("creator"),
                })

    if len(images) == 0:
        return None

    images = _repeat_images(images)

    match key:
        case "playlist-top-discoveries-for-year":
            target_svg = "art/svg-templates/year-in-music/legacy/2024/yim-2024-discovery-playlist.svg"
        case "playlist-top-missed-recordings-for-year":
            target_svg = "art/svg-templates/year-in-music/legacy/2024/yim-2024-missed-tracks-playlist.svg"
        case other:
            raise APIBadRequest(f"Invalid playlist type {key}. Playlist type should be one of (playlist-top-discoveries-for-year, playlist-top-missed-recordings-for-year)")

    return render_template(
        target_svg,
        user_name=user_name,
        images=images,
        branding=branding,
        **yim24,
    )


def legacy_cover_art_yim_playlist(user_name, stats, key, year, branding, yim24):
    """ Create the SVG using playlist tracks' cover arts for the given YIM playlist. """
    if year == 2022:
        return _cover_art_yim_playlist_2022(user_name, stats, key)

    if year == 2023:
        return _cover_art_yim_playlist_2023(user_name, stats, key, branding)

    if year == 2024:
        return _cover_art_yim_playlist_2024(user_name, stats, key, branding, yim24)


def legacy_cover_art_yim_overview(user_name, stats, year, yim24):
    """ Create the SVG using top stats for the overview YIM image. """
    filtered_genres = []
    total_filtered_genre_count = 0
    number_of_genres = 4 if year < 2024 else 6
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
        "album_2": album_2
    }

    if year == 2023:
        return render_template("art/svg-templates/year-in-music/legacy/2023/yim-2023.svg", **props)

    if year == 2024:
        return render_template("art/svg-templates/year-in-music/legacy/2024/yim-2024-overview.svg", **props, **yim24)



def cover_art_yim_legacy(user, image: str, year: int = 2024, branding: bool = True):
    """ Create the shareable svg image using YIM stats """
    user_name = user["musicbrainz_id"]
    stats = db_yim.get(user["id"], year, legacy=True)
    if stats is None:
        raise APIBadRequest(f"Year In Music {year} report for user {user_name} not found")

    season = request.args.get("season") or 'spring'
    match season:
        case "spring":
            background_color = "#EDF3E4"
            accent_color = "#2B9F7A"
        case "summer":
            background_color = "#DBE8DF"
            accent_color = "#3C8C54"
        case "autumn":
            background_color = "#F1E8E1"
            accent_color = "#CB3146"
        case "winter":
            background_color = "#DFE5EB"
            accent_color = "#5B52AC"

    # todo: use legacy query param here when new YIM images are ready
    yim24 = None
    if year == 2024:
        yim24 = {
            "season": season,
            "background_color": background_color,
            "accent_color": accent_color,
            "image_folder": f'{current_app.config["SERVER_ROOT_URL"]}/static/img/year-in-music-24/{season}',
        }

    match image:
        case "overview": svg = legacy_cover_art_yim_overview(user_name, stats, year, yim24)
        case "stats": svg = legacy_cover_art_yim_stats(user_name, stats, year, yim24)
        case "albums": svg = legacy_cover_art_yim_albums(user_name, stats, year, yim24)
        case "tracks": svg = legacy_cover_art_yim_tracks(user_name, stats, year, yim24)
        case "artists": svg = legacy_cover_art_yim_artists(user_name, stats, year, yim24)
        case "discovery-playlist": svg = legacy_cover_art_yim_playlist(user_name, stats, "playlist-top-discoveries-for-year", year, branding, yim24)
        case "missed-playlist": svg = legacy_cover_art_yim_playlist(user_name, stats, "playlist-top-missed-recordings-for-year", year, branding, yim24)
        case other: raise APIBadRequest(f"Invalid image type {other}. Image type should be one of (stats, artists, albums, tracks, discovery-playlist, missed-playlist)")

    if svg is None:
        return "", 204

    return svg, 200, {"Content-Type": "image/svg+xml"}
