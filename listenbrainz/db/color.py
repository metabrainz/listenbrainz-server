import psycopg2

#from listenbrainz import db
from brainzutils import musicbrainz_db as db  # Temporary
from listenbrainz.db.model.color import ColorResult, ColorCube
from typing import List
from psycopg2.extensions import adapt, AsIs, register_adapter


def adapt_cube(cube):
    """ Function required by Postgres for inserting/searching cube extension colors """
    return AsIs("'(%s, %s, %s)'" % (adapt(cube.red), adapt(cube.green), adapt(cube.blue)))


register_adapter(ColorCube, adapt_cube)


def get_releases_for_color(red: int, green: int, blue: int, count: int) -> List[ColorResult]:
    """ Fetch matching releases, their euclidian distance in RGB space and the
        release_name and artist_name for the returned releases.

        Args:
          red, green, blue: ints for each of the red, green and blue color components.
          count: int -- the number of matches to return
        Returns:
          A list of ColorResult objects.
    """

    query = """SELECT release_mbid::TEXT
                    , caa_id
                    , red
                    , green
                    , blue
                    , cube_distance(color, %s) AS dist
                 FROM release_colors
             ORDER BY cube_distance(color, %s) 
                LIMIT %s"""

    cube = ColorCube(red=red, green=green, blue=blue)
    args = (cube, cube, count)

    mb_query = """SELECT r.gid::TEXT AS release_mbid
                       , r.name AS release_name
                       , ac.name AS artist_credit_name
                    FROM release r
                    JOIN artist_credit ac
                      ON r.artist_credit = ac.id
                   WHERE r.gid in %s"""

    conn = db.engine.raw_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

        results = []
        mbids = []
        index = {}
        curs.execute(query, args)
        for i, row in enumerate(curs.fetchall()):
            results.append(ColorResult(release_mbid=row["release_mbid"],
                                       caa_id=row["caa_id"],
                                       color=ColorCube(red=row["red"], green=row["green"], blue=row["blue"]),
                                       distance=row["dist"]))
            index[row["release_mbid"]] = i
            mbids.append(row["release_mbid"])

        curs.execute(mb_query, (tuple(mbids),))
        for row in curs.fetchall():
            i = index[row["release_mbid"]]
            results[i].release_name = row["release_name"]
            results[i].artist_name = row["artist_credit_name"]

        return results
