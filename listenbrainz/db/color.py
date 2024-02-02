import psycopg2

from listenbrainz import db
from brainzutils import musicbrainz_db as mb_db
from listenbrainz.db.model.color import ColorResult, ColorCube
from typing import List, Dict
from psycopg2.extensions import adapt, AsIs, register_adapter

# This determines how many releases for a given color are fetched and then randomly chosen from.
# If COUNT releases are requested, we use COUNT * INTERMEDIARY_COUNT_MULTIPLIER to create
# the possible set to choose from. If this number is too large, we may get too much color variability
# in the results and if it is too small, we get no variability at all.
INTERMEDIARY_COUNT_MULTIPLIER = 4


def adapt_cube(cube):
    """ Function required by Postgres for inserting/searching cube extension colors """
    return AsIs("'(%s, %s, %s)'" % (adapt(cube.red), adapt(cube.green), adapt(cube.blue)))


register_adapter(ColorCube, adapt_cube)


def get_releases_for_color(db_conn, red: int, green: int, blue: int, count: int) -> List[ColorResult]:
    """ Fetch matching releases, their euclidian distance in RGB space and the
        release_name and artist_name for the returned releases.

        Args:
          red, green, blue: ints for each of the red, green and blue color components.
          count: int -- the number of matches to return
        Returns:
          A list of ColorResult objects.
    """

    query = """SELECT release_mbid
                   , caa_id
                   , red
                   , green
                   , blue
                   , dist                                         
                FROM (SELECT release_mbid::TEXT
                           , caa_id
                           , red
                           , green
                           , blue
                           , cube_distance(color, %s) AS dist
                           , random() AS sort_order
                       FROM release_color
                      ORDER BY dist
                      LIMIT %s) AS hs
                ORDER BY sort_order
                   LIMIT %s"""

    cube = ColorCube(red=red, green=green, blue=blue)
    args = (cube, INTERMEDIARY_COUNT_MULTIPLIER * count, count)

    mb_query = """SELECT rec.name AS recording_name
                       , rec.gid::TEXT AS recording_mbid
                       , r.gid::TEXT AS release_mbid
                       , r.name AS release_name
                       , ac.name AS artist_credit_name
                       , array_agg(a.gid::TEXT) AS artist_mbids
                    FROM release r
                    JOIN artist_credit ac
                      ON r.artist_credit = ac.id
                    JOIN artist_credit_name acn
                      ON acn.artist_credit = ac.id
                    JOIN artist a
                      ON acn.artist = a.id
                    JOIN medium m
                      ON m.release = r.id
                    JOIN track t
                      ON t.medium = m.id
                    JOIN recording rec
                      ON t.recording = rec.id
                   WHERE r.gid in %s
                GROUP BY r.gid, r.name, t.position, rec.gid, rec.name, ac.name
                ORDER BY r.gid, t.position"""

    with db_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        results = []
        mbids = []
        index = {}
        curs.execute(query, args)
        for i, row in enumerate(curs.fetchall()):
            index[row["release_mbid"]] = i
            mbids.append(row["release_mbid"])
            results.append(ColorResult(release_mbid=row["release_mbid"],
                                       caa_id=row["caa_id"],
                                       color=ColorCube(red=row["red"], green=row["green"], blue=row["blue"]),
                                       distance=row["dist"]))

        if mb_db.engine is not None:
            mb_conn = mb_db.engine.raw_connection()
            with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
                recordings = []
                last_release_mbid = None
                mb_curs.execute(mb_query, (tuple(mbids),))
                for row in mb_curs.fetchall():
                    if last_release_mbid is not None and last_release_mbid != row["release_mbid"]:
                        i = index[last_release_mbid]
                        results[i].release_name = recordings[0]["track_metadata"]["release_name"]
                        results[i].artist_name = recordings[0]["track_metadata"]["artist_name"]
                        results[i].rec_metadata = recordings
                        recordings = []

                    recordings.append({
                        "track_metadata": {
                            "track_name": row["recording_name"],
                            "release_name": row["release_name"],
                            "artist_name": row["artist_credit_name"],
                            "additional_info": {
                                "recording_mbid": row["recording_mbid"],
                                "release_mbid": row["release_mbid"],
                                "artist_mbids": row["artist_mbids"]
                            }
                        }
                    })
                    last_release_mbid = row["release_mbid"]

                if recordings:
                    i = index[last_release_mbid]
                    results[i].release_name = recordings[0]["track_metadata"]["release_name"]
                    results[i].artist_name = recordings[0]["track_metadata"]["artist_name"]
                    results[i].rec_metadata = recordings

        return results


def fetch_color_for_releases(db_conn, release_mbids: List[str]) -> Dict[str, Dict[str, int]]:
    """ Fetch the color for a given list of release mbids. If the release does not have a color
        associated with it, None is returned.

        Args:
          db_conn: database connection
          release_mbids: List[str] -- the mbids for the releases
        Returns:
          Returns a dict with the keys red, green and blue or None if no color is found.
    """

    if not release_mbids:
        return {}

    query = """SELECT release_mbid,
                      red,
                      green,
                      blue
                 FROM release_color
                WHERE release_mbid in %s
             ORDER BY last_updated DESC"""

    with db_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (tuple(release_mbids),))
        rows = curs.fetchall()
        data = {}
        for row in rows:
            data[str(row["release_mbid"])] = {
                "red": row["red"],
                "green": row["green"],
                "blue": row["blue"]
            }
        return data
