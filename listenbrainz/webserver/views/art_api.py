#!/usr/bin/env python3
import datetime
from uuid import UUID

from flask import Flask, send_file, request, Response, render_template
import psycopg2
import psycopg2.extras
from psycopg2.errors import OperationalError
import requests
from werkzeug.exceptions import BadRequest, InternalServerError

import config

art_api_bp = Blueprint('art_api_v1', __name__)

@app.route("/")
def index():
    return render_template("index.html", width="750", height="750")

@app.route("/coverart/grid/", methods=["POST"])
def cover_art_grid_post():

    r = request.json

    if "tiles" in r:
        cac = CoverArtGenerator(r["dimension"], r["image_size"], r["background"], r["skip-missing"], r["show-caa"])
        tiles = r["tiles"]
    else:
        if "layout" in r:
            layout = r["layout"]
        else:
            layout = 0
        cac = CoverArtGenerator(r["dimension"], r["image_size"], r["background"], r["skip-missing"], r["show-caa"], r["layout"])
        tiles = None

    err = cac.validate_parameters()
    if err is not None:
        raise BadRequest(err)

    if not isinstance(r["release_mbids"], list):
        raise BadRequest("release_mbids must be a list of strings specifying release_mbids")

    for mbid in r["release_mbids"]:
        try:
            UUID(mbid)
        except ValueError:
            raise BadRequest(f"Invalid release_mbid {mbid} specified.")

    images = cac.load_images(r["release_mbids"], tile_addrs=tiles)
    if images is None:
        raise InternalServerError("Failed to grid cover art SVG")

    return render_template("svg-templates/simple-grid.svg",
                           background=r["background"],
                           images=images,
                           width=r["image_size"],
                           height=r["image_size"]), 200, {'Content-Type': 'image/svg+xml'}


@app.route("/coverart/grid-stats/<user_name>/<time_range>/<int:dimension>/<int:layout>/<int:image_size>", methods=["GET"])
def cover_art_grid_stats(user_name, time_range, dimension, layout, image_size):

    cac = CoverArtGenerator(dimension, image_size)
    err = cac.validate_parameters()
    if err is not None:
        raise BadRequest(err)

    try:
        _ = cac.GRID_TILE_DESIGNS[dimension][layout]
    except IndexError:
        return f"layout {layout} is not available for dimension {dimension}."

    images, _ = cac.create_grid_stats_cover(user_name, time_range, layout)
    if images is None:
        raise InternalServerError("Failed to create composite image.")

    return render_template("svg-templates/simple-grid.svg",
                           background=cac.background,
                           images=images,
                           width=image_size,
                           height=image_size), 200, {'Content-Type': 'image/svg+xml'}


@app.route("/coverart/<custom_name>/<user_name>/<time_range>/<int:image_size>", methods=["GET"])
def cover_art_custom_stats(custom_name, user_name, time_range, image_size):

    cac = CoverArtGenerator(3, image_size)
    err = cac.validate_parameters()
    if err is not None:
        raise BadRequest(err)

    if custom_name in ("designer-top-5"):
        artists, metadata = cac.create_artist_stats_cover(user_name, time_range)
        return render_template(f"svg-templates/{custom_name}.svg", 
                               artists=artists,
                               width=image_size,
                               height=image_size,
                               metadata=metadata), 200, {'Content-Type': 'image/svg+xml'}

    if custom_name in ("lps-on-the-floor", "designer-top-10", "designer-top-10-alt"):
        images, releases, metadata = cac.create_release_stats_cover(user_name, time_range)
        return render_template(f"svg-templates/{custom_name}.svg", 
                               images=images,
                               releases=releases,
                               width=image_size,
                               height=image_size,
                               metadata=metadata), 200, {'Content-Type': 'image/svg+xml'}

    raise BadRequest(f"Unkown custom cover art type {custom_name}")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
