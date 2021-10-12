import psycopg2

#from listenbrainz import db
from brainzutils import musicbrainz_db as db  # Temporary
from listenbrainz.db.model.color import ColorResult, ColorCube
from typing import List
from psycopg2.extensions import adapt, AsIs, register_adapter


def adapt_cube(cube):
    return AsIs("'(%s, %s, %s)'" % (adapt(cube.red), adapt(cube.green), adapt(cube.blue)))

register_adapter(ColorCube, adapt_cube)

def get_releases_for_color(red: int, green: int, blue: int, count: int ) -> List[ColorResult]:

    query = """SELECT release_mbid::TEXT
                    , red
                    , green
                    , blue
                    , cube_distance(color, %s) AS dist
                 FROM release_colors
             ORDER BY cube_distance(color, %s) 
                LIMIT %s"""

    cube = ColorCube(red=red, green=green, blue=blue)
    args = ( cube, cube, count )

    conn = db.engine.raw_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

        results = []
        curs.execute(query, args)
        for row in curs.fetchall():
            results.append(ColorResult(release_mbid=row["release_mbid"],
                                       color=ColorCube(red=row["red"], green=row["green"], blue=row["blue"]),
                                       distance=row["dist"]))

        return results
