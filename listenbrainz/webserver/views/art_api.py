import datetime

from flask import Flask, request, render_template, Blueprint, current_app
import psycopg2
import psycopg2.extras
from psycopg2.errors import OperationalError
import requests

from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError
from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.webserver.decorators import crossdomain
from brainzutils.ratelimit import ratelimit


art_api_bp = Blueprint('art_api_v1', __name__)

@art_api_bp.route("/grid/", methods=["POST"])
@crossdomain
@ratelimit()
def cover_art_grid_post():

    r = request.json

    if "tiles" in r:
        cac = CoverArtGenerator(current_app.config["MB_DATABASE_URI"], r["dimension"], r["image_size"],
                                r["background"], r["skip-missing"], r["show-caa"])
        tiles = r["tiles"]
    else:
        if "layout" in r:
            layout = r["layout"]
        else:
            layout = 0
        cac = CoverArtGenerator(current_app.config["MB_DATABASE_URI"], r["dimension"], r["image_size"],
                                r["background"], r["skip-missing"], r["show-caa"], r["layout"])
        tiles = None

    err = cac.validate_parameters()
    if err is not None:
        raise APIBadRequest(err)

    if not isinstance(r["release_mbids"], list):
        raise APIBadRequest("release_mbids must be a list of strings specifying release_mbids")

    for mbid in r["release_mbids"]:
        try:
            UUID(mbid)
        except ValueError:
            raise APIBadRequest(f"Invalid release_mbid {mbid} specified.")

    images = cac.load_images(r["release_mbids"], tile_addrs=tiles)
    if images is None:
        raise APIInternalServerError("Failed to grid cover art SVG")

    return render_template("art/svg-templates/simple-grid.svg",
                           background=r["background"],
                           images=images,
                           width=r["image_size"],
                           height=r["image_size"]), 200, {'Content-Type': 'image/svg+xml'}


@art_api_bp.route("/grid-stats/<user_name>/<time_range>/<int:dimension>/<int:layout>/<int:image_size>", methods=["GET"])
@crossdomain
@ratelimit()
def cover_art_grid_stats(user_name, time_range, dimension, layout, image_size):

    cac = CoverArtGenerator(current_app.config["MB_DATABASE_URI"], dimension, image_size)
    err = cac.validate_parameters()
    if err is not None:
        raise APIBadRequest(err)

    try:
        _ = cac.GRID_TILE_DESIGNS[dimension][layout]
    except IndexError:
        return f"layout {layout} is not available for dimension {dimension}."

    try:
        images, _ = cac.create_grid_stats_cover(user_name, time_range, layout)
        if images is None:
            raise APIInternalServerError("Failed to grid cover art SVG")
    except ValueError as error:
        raise APIBadRequest(error)

    return render_template("art/svg-templates/simple-grid.svg",
                           background=cac.background,
                           images=images,
                           width=image_size,
                           height=image_size), 200, {'Content-Type': 'image/svg+xml'}


@art_api_bp.route("/<custom_name>/<user_name>/<time_range>/<int:image_size>", methods=["GET"])
@crossdomain
@ratelimit()
def cover_art_custom_stats(custom_name, user_name, time_range, image_size):

    cac = CoverArtGenerator(current_app.config["MB_DATABASE_URI"], 3, image_size)
    err = cac.validate_parameters()
    if err is not None:
        raise APIBadRequest(err)

    if custom_name in ("designer-top-5"):
        try:
            artists, metadata = cac.create_artist_stats_cover(user_name, time_range)
            if artists is None:
                raise APIInternalServerError("Failed to artist cover art SVG")
        except ValueError as error:
            raise APIBadRequest(error)

        return render_template(f"/art/svg-templates/{custom_name}.svg", 
                               artists=artists,
                               width=image_size,
                               height=image_size,
                               metadata=metadata), 200, {'Content-Type': 'image/svg+xml'}

    if custom_name in ("lps-on-the-floor", "designer-top-10", "designer-top-10-alt"):
        try:
            images, releases, metadata = cac.create_release_stats_cover(user_name, time_range)
            if images is None:
                raise APIInternalServerError("Failed to release cover art SVG")
        except ValueError as error:
            raise APIBadRequest(error)

        return render_template(f"art/svg-templates/{custom_name}.svg", 
                               images=images,
                               releases=releases,
                               width=image_size,
                               height=image_size,
                               metadata=metadata), 200, {'Content-Type': 'image/svg+xml'}

    raise APIBadRequest(f"Unkown custom cover art type {custom_name}")
