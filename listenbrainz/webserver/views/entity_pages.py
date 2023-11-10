from flask import Blueprint, render_template, current_app
from flask_login import current_user, login_required
from listenbrainz import webserver
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.db import timescale
from listenbrainz.db.metadata import get_metadata_for_artist
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.db.popularity import get_top_entity_for_entity
from listenbrainz.webserver.views.metadata_api import fetch_release_group_metadata
import requests
from werkzeug.exceptions import BadRequest, NotFound
import orjson
import psycopg2
import psycopg2.extras

artist_bp = Blueprint("artist", __name__)
album_bp = Blueprint("album", __name__)


@artist_bp.route("/<artist_mbid>", methods=["GET"])
@web_listenstore_needed
def artist_entity(artist_mbid):
    """ Show a artist page with all their relevant information """

    if not is_valid_uuid(artist_mbid):
        raise BadRequest("Provided artist ID is invalid: %s" % artist_mbid)

    # Fetch the artist cached data
    artist_data = get_metadata_for_artist([artist_mbid])
    if len(artist_data) == 0:
        raise NotFound(f"artist {artist_mbid} not found in the metadata cache")

    artists_no_uuid = []
    for artist in artist_data:
        artist.artist_mbid = str(artist.artist_mbid)
        artists_no_uuid.append(artist)

    artist_data = artists_no_uuid

    item = {"artist_mbid": artist_data[0].artist_mbid}
    item.update(**artist_data[0].artist_data)
    item["tag"] = artist_data[0].tag_data

    # Fetch top recordings for artist
    params = {"artist_mbid": artist_mbid, 'count': 10}
    r = requests.get(url="https://api.listenbrainz.org/1/popularity/top-recordings-for-artist", params=params)
    if r.status_code != 200:
        popular_recordings = []
    else:
        popular_recordings = list(r.json())[:10]

    # Fetch similar artists
    r = requests.post("https://labs.api.listenbrainz.org/similar-artists/json",
                      json=[{
                          'artist_mbid':
                          artist_mbid,
                          'algorithm':
                          "session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30"
                      }])

    if r.status_code != 200:
        raise RuntimeError(f"Cannot fetch similar artists: {r.status_code} ({r.text})")

    try:
        artists = r.json()[3]["data"][:15]
    except IndexError:
        artists = []

    # General note: This whole view function is a disaster, yes. But it is only so that monkey can work on the
    # UI for these pages. The next project will be to collect all this data and store it in couchdb.
    top_release_groups = get_top_entity_for_entity("release-group", artist_mbid, "release-group")
    release_group_mbids = tuple([str(k["release_group_mbid"]) for k in top_release_groups])

    query = """SELECT DISTINCT ON (rg.id)
                   rg.gid::TEXT AS release_group_mbid
                 , rg.name AS release_group_name
                 , (re.date_year::TEXT || '-' || 
                    LPAD(re.date_month::TEXT, 2, '0') || '-' || 
                    LPAD(re.date_day::TEXT, 2, '0')) AS date
                 , rgpt.name AS type
                 , caa.id AS caa_id
                 , caa_rel.gid::TEXT AS caa_release_mbid
              FROM musicbrainz.release_group rg
              JOIN musicbrainz.release_group_primary_type rgpt
                ON rg.type = rgpt.id
              JOIN musicbrainz.release caa_rel
                ON rg.id = caa_rel.release_group
         LEFT JOIN (
                  SELECT release, date_year, date_month, date_day
                    FROM musicbrainz.release_country
               UNION ALL
                  SELECT release, date_year, date_month, date_day
                    FROM musicbrainz.release_unknown_country
                 ) re
                ON (re.release = caa_rel.id)
         FULL JOIN cover_art_archive.release_group_cover_art rgca
                ON rgca.release = caa_rel.id
         LEFT JOIN cover_art_archive.cover_art caa
                ON caa.release = caa_rel.id
         LEFT JOIN cover_art_archive.cover_art_type cat
                ON cat.id = caa.id
             WHERE type_id = 1
               AND mime_type != 'application/pdf'
               AND rg.gid in %s
          ORDER BY rg.id
                 , rgca.release
                 , re.date_year
                 , re.date_month
                 , re.date_day
                 , caa.ordering"""

    release_groups = []
    if len(release_group_mbids) > 0:
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn:
            with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
                mb_curs.execute(query, (release_group_mbids, ))
                release_groups = [dict(row) for row in mb_curs.fetchall()]

    props = {
        "artist_data": item,
        "popular_recordings": popular_recordings,
        "similar_artists": artists,
        "listening_stats": {},  #for that artist,  # DO NOT IMPLEMENT RIGHT NOW. WAIT FOR PROPER CACHING
        # total plays for artist
        # total # of listeners for artist
        # top listeners (10)
        "release_groups": release_groups
    }

    return render_template("entities/artist.html",
                           props=orjson.dumps(props).decode("utf-8"),
                           title=artist_data[0].artist_data["name"])


@album_bp.route("/<release_group_mbid>", methods=["GET"])
@web_listenstore_needed
def album_entity(release_group_mbid):
    """ Show an album page with all their relevant information """

    if not is_valid_uuid(release_group_mbid):
        raise BadRequest("Provided release group ID is invalid: %s" % release_group_mbid)

    # Fetch the release group cached data
    metadata = fetch_release_group_metadata([release_group_mbid], ["artist", "tag", "release"])
    if len(metadata) == 0:
        raise NotFound(f"Release group {release_group_mbid} not found in the metadata cache")

    # TODO:
    #- release_group tracks with listen count

    query = """WITH release_group_data AS (
                   SELECT DISTINCT ON (rg.id)
                          rgpt.name AS type
                        , (re.date_year::TEXT || '-' || 
                           LPAD(re.date_month::TEXT, 2, '0') || '-' || 
                           LPAD(re.date_day::TEXT, 2, '0')) AS date
                        , caa.id AS caa_id
                        , caa_rel.gid::TEXT AS caa_release_mbid
                     FROM musicbrainz.release_group rg
                     JOIN musicbrainz.release_group_primary_type rgpt
                       ON rg.type = rgpt.id
                     JOIN musicbrainz.release caa_rel
                       ON rg.id = caa_rel.release_group
                LEFT JOIN (
                         SELECT release, date_year, date_month, date_day
                           FROM musicbrainz.release_country
                      UNION ALL
                         SELECT release, date_year, date_month, date_day
                           FROM musicbrainz.release_unknown_country
                        ) re
                       ON (re.release = caa_rel.id)
                FULL JOIN cover_art_archive.release_group_cover_art rgca
                       ON rgca.release = caa_rel.id
                LEFT JOIN cover_art_archive.cover_art caa
                       ON caa.release = caa_rel.id
                LEFT JOIN cover_art_archive.cover_art_type cat
                       ON cat.id = caa.id
                    WHERE type_id = 1
                      AND mime_type != 'application/pdf'
                      AND rg.gid = %s
                 ORDER BY rg.id
                        , rgca.release
                        , re.date_year
                        , re.date_month
                        , re.date_day
                        , caa.ordering
                ), recording_data AS (
                   SELECT rel.gid AS release_mbid
                        , array_agg(jsonb_build_array(t.position, r.name, r.gid::TEXT, r.length)) AS recordings
                     FROM release rel
                     JOIN medium m
                       ON m.release = rel.id
                     JOIN track t
                       ON t.medium = m.id
                     JOIN recording r
                       ON r.id = t.recording
                     JOIN release_group_data rgd
                       ON rgd.caa_release_mbid::uuid = rel.gid
                 GROUP BY rel.gid
                )
                   SELECT type
                        , date
                        , caa_id
                        , caa_release_mbid::TEXT
                        , recordings
                    FROM release_group_data rgd
                    JOIN recording_data rg
                      ON rgd.caa_release_mbid::uuid = rg.release_mbid"""

    pop_query = """SELECT recording_mbid::TEXT
                        , total_listen_count
                        , total_user_count
                     FROM popularity.recording
                    WHERE recording_mbid in %s"""
    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            mb_curs.execute(query, (release_group_mbid, ))
            release_groups_caa_type = dict(mb_curs.fetchone())

    recording_mbids = [rec[2] for rec in release_groups_caa_type["recordings"]]
    with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as lb_conn:
        with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            lb_curs.execute(pop_query, (tuple(recording_mbids), ))
            popularity = [dict(row) for row in lb_curs.fetchall()]

    pop_index = {row["recording_mbid"]: (row["total_listen_count"], row["total_user_count"]) for row in popularity}

    recordings = []
    for rec in release_groups_caa_type["recordings"]:
        recording = {"position": rec[0], "name": rec[1], "recording_mbid": rec[2], "length": rec[3]}
        try:
            recording["total_listen_count"] = pop_index[rec[2]][0]
            recording["total_user_count"] = pop_index[rec[2]][1]
        except KeyError:
            recording["total_listen_count"] = None
            recording["total_user_count"] = None
        recordings.append(recording)

    props = metadata[release_group_mbid]
    props["release_group_mbid"] = release_group_mbid
    props["type"] = release_groups_caa_type["type"]
    props["caa_id"] = release_groups_caa_type["caa_id"]
    props["caa_release_mbid"] = release_groups_caa_type["caa_release_mbid"]
    props["recordings"] = recordings
    #import json
    #current_app.logger.warn(json.dumps(props, indent=4, sort_keys=True))

    return render_template("entities/album.html",
                           props=orjson.dumps(props).decode("utf-8"),
                           title=metadata[release_group_mbid]["release_group"]["name"])
