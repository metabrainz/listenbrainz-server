from operator import attrgetter

import sqlalchemy

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.model.color import ColorCube
from listenbrainz.db.color import get_releases_for_color


class HuesoundTestCase(DatabaseTestCase):

    def insert_test_data(self):
        self.db_conn.execute(sqlalchemy.text("""INSERT INTO release_color (caa_id, release_mbid, red, green, blue, color)
                                                VALUES (1, 'e97f805a-ab48-4c52-855e-07049142113d', 0, 0, 255, '(0, 0, 255)')"""))
        self.db_conn.execute(sqlalchemy.text("""INSERT INTO release_color (caa_id, release_mbid, red, green, blue, color)
                                                VALUES (2, '7ffff8fc-cd98-47af-9805-5fac5f9d2e04', 255,  0, 255, '(255, 0, 255)')"""))
        self.db_conn.execute(sqlalchemy.text("""INSERT INTO release_color (caa_id, release_mbid, red, green, blue, color)
                                                VALUES (3, '8c276439-d5e8-4560-8df0-2b7c996fd1a4', 255, 0, 0, '(255, 0, 0)')"""))

    def test_get_releases_for_color(self):

        self.insert_test_data()
        r = get_releases_for_color(self.db_conn, 255, 0, 0, 3)

        # Results need to be sorted in order to undo the randomness of this function.
        r = sorted(r, key=attrgetter("caa_id"))
        self.assertEqual(3, len(r))

        self.assertEqual(r[0].caa_id, 1)
        self.assertEqual(r[0].release_mbid, "e97f805a-ab48-4c52-855e-07049142113d")
        self.assertEqual(r[0].color, ColorCube(red=0, green=0, blue=255))

        self.assertEqual(r[1].caa_id, 2)
        self.assertEqual(r[1].release_mbid, "7ffff8fc-cd98-47af-9805-5fac5f9d2e04")
        self.assertEqual(r[1].color, ColorCube(red=255, green=0, blue=255))

        self.assertEqual(r[2].caa_id, 3)
        self.assertEqual(r[2].release_mbid, "8c276439-d5e8-4560-8df0-2b7c996fd1a4")
        self.assertEqual(r[2].color, ColorCube(red=255, green=0, blue=0))
