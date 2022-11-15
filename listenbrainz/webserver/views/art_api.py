import datetime
import os
from uuid import UUID

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

ART_API_SUBDOMAIN = "api" if os.environ.get("DEPLOY_ENV", "") != "" else ""


@art_api_bp.route("/grid/", methods=["POST"], subdomain=ART_API_SUBDOMAIN)
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
                          on the tiles defined by the tiles parameter.
    :type release_mbids: ``list``

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

    cac = CoverArtGenerator(current_app.config["MB_DATABASE_URI"], r["dimension"], r["image_size"], r["background"],
                            r["skip-missing"], r["show-caa"])

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

    images = cac.load_images(r["release_mbids"], tile_addrs=tiles, layout=layout)
    if images is None:
        raise APIInternalServerError("Failed to grid cover art SVG")

    return render_template("art/svg-templates/simple-grid.svg",
                           background=r["background"],
                           images=images,
                           width=r["image_size"],
                           height=r["image_size"]), 200, {
                               'Content-Type': 'image/svg+xml'
                           }


@art_api_bp.route("/grid-stats/<user_name>/<time_range>/<int:dimension>/<int:layout>/<int:image_size>",
                  methods=["GET"],
                  subdomain=ART_API_SUBDOMAIN)
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
    :statuscode 200: cover art created successfully.
    :statuscode 400: Invalid JSON or invalid options in JSON passed. See error message for details.
    :resheader Content-Type: *image/svg+xml*

    See the bottom of this document for constants relating to this method.
    """

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
                           height=image_size), 200, {
                               'Content-Type': 'image/svg+xml'
                           }


@art_api_bp.route("/<custom_name>/<user_name>/<time_range>/<int:image_size>", methods=["GET"], subdomain=ART_API_SUBDOMAIN)
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
        except ValueError as error:
            raise APIBadRequest(error)

        return render_template(f"art/svg-templates/{custom_name}.svg",
                               images=images,
                               releases=releases,
                               width=image_size,
                               height=image_size,
                               metadata=metadata), 200, {
                                   'Content-Type': 'image/svg+xml'
                               }

    raise APIBadRequest(f"Unkown custom cover art type {custom_name}")
