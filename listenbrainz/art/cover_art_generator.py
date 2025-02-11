import datetime

import psycopg2
import psycopg2.extras

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from data.model.common_stat import StatisticsRange
from data.model.user_entity import EntityRecord

from listenbrainz.db.cover_art import get_caa_ids_for_release_mbids, get_caa_ids_for_release_group_mbids
from listenbrainz.webserver import db_conn

#: Minimum image size
MIN_IMAGE_SIZE = 128

#: Maximum image size
MAX_IMAGE_SIZE = 1024

#: Minimum dimension
MIN_DIMENSION = 1

#: Maximum dimension
MAX_DIMENSION = 5

#: Number of stats to fetch
NUMBER_OF_STATS = 100


class CoverArtGenerator:
    """ Main engine for generating dynamic cover art. Given a design and data (e.g. stats) generate
        cover art from cover art images or text using the SVG format. """

    CAA_MISSING_IMAGE = "https://listenbrainz.org/static/img/cover-art-placeholder.jpg"

    # This grid tile designs (layouts?) are expressed as a dict with they key as dimension.
    # The value of the dict defines one design, with each cell being able to specify one or
    # more number of cells. Each string is a list of cells that will be used to define
    # the bounding box of these cells. The cover art in question will be placed inside this
    # area.
    GRID_TILE_DESIGNS = {
        1: [
            ["0"],
        ],
        2: [
            ["0", "1", "2", "3"],
        ],
        3: [
            ["0", "1", "2", "3", "4", "5", "6", "7", "8"],
            ["0,1,3,4", "2", "5", "6", "7", "8"],
            ["0", "1", "2", "3", "4,5,7,8", "6"],
        ],
        4: [
            ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
            ["5,6,9,10", "0", "1", "2", "3", "4", "7", "8", "11", "12", "13", "14", "15"],
            ["0,1,4,5", "10,11,14,15", "2", "3", "6", "7", "8", "9", "12", "13"],
            ["0,1,2,4,5,6,8,9,10", "3", "7", "11", "12", "13", "14", "15"],
        ],
        5: [[
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
            "21", "22", "23", "24"
        ], ["0,1,2,5,6,7,10,11,12", "3,4,8,9", "15,16,20,21", "13", "14", "17", "18", "19", "22", "23", "24"]]
    }

    # Take time ranges and give correct english text
    time_range_to_english = {
        "week": "last week",
        "month": "last month",
        "quarter": "last quarter",
        "half_yearly": "last 6 months",
        "year": "last year",
        "all_time": "of all time",
        "this_week": "this week",
        "this_month": "this month",
        "this_year": "this year"
    }

    def __init__(self,
                 mb_db_connection_str,
                 dimension,
                 image_size,
                 background="#FFFFFF",
                 skip_missing=True,
                 show_caa_image_for_missing_covers=True):
        self.mb_db_connection_str = mb_db_connection_str
        self.dimension = dimension
        self.image_size = image_size
        self.background = background
        self.skip_missing = skip_missing
        self.show_caa_image_for_missing_covers = show_caa_image_for_missing_covers
        self.tile_size = image_size // dimension  # This will likely need more cafeful thought due to round off errors

    def parse_color_code(self, color_code):
        """ Parse an HTML color code that starts with # and return a tuple(red, green, blue) """

        if not color_code.startswith("#"):
            return None

        try:
            r = int(color_code[1:3], 16)
        except ValueError:
            return None

        try:
            g = int(color_code[3:5], 16)
        except ValueError:
            return None

        try:
            b = int(color_code[5:7], 16)
        except ValueError:
            return None

        return r, g, b

    def validate_parameters(self):
        """ Validate the parameters for the cover art designs. """

        if self.dimension not in list(range(MIN_DIMENSION, MAX_DIMENSION + 1)):
            return "dimension must be between {MIN_DIMENSION} and {MAX_DIMENSION}, inclusive."

        bg_color = self.parse_color_code(self.background)
        if self.background not in ("transparent", "white", "black") and bg_color is None:
            return f"background must be one of transparent, white, black or a color code #rrggbb, not {self.background}"

        if self.image_size < MIN_IMAGE_SIZE or self.image_size > MAX_IMAGE_SIZE or self.image_size is None:
            return f"image size must be between {MIN_IMAGE_SIZE} and {MAX_IMAGE_SIZE}, inclusive."

        if not isinstance(self.skip_missing, bool):
            return f"option skip-missing must be of type boolean."

        if not isinstance(self.show_caa_image_for_missing_covers, bool):
            return f"option show-caa must be of type boolean."

        return None

    def get_tile_position(self, tile):
        """ Calculate the position of a given tile, return (x1, y1, x2, y2). The math
            in this setup may seem a bit wonky, but that is to ensure that we don't have
            round-off errors that will manifest as line artifacts on the resultant covers"""

        if tile < 0 or tile >= self.dimension * self.dimension:
            return (None, None)

        x = tile % self.dimension
        y = tile // self.dimension

        x1 = int(x * self.tile_size)
        y1 = int(y * self.tile_size)
        x2 = int((x + 1) * self.tile_size)
        y2 = int((y + 1) * self.tile_size)

        if x == self.dimension - 1:
            x2 = self.image_size
        if y == self.dimension - 1:
            y2 = self.image_size

        return (x1, y1, x2, y2)

    def calculate_bounding_box(self, address):
        """ Given a cell 'address' return its bounding box. An address is a list of comma separeated
            grid cells, which taken collectively present a bounding box for a cover art image."""

        try:
            tiles = address.split(",")
            for i in range(len(tiles)):
                tiles[i] = int(tiles[i].strip())
        except (ValueError, TypeError):
            return None, None, None, None

        for tile in tiles:
            if tile < 0 or tile >= (self.dimension * self.dimension):
                return None, None, None, None

        for i, tile in enumerate(tiles):
            x1, y1, x2, y2 = self.get_tile_position(tile)

            if i == 0:
                bb_x1 = x1
                bb_y1 = y1
                bb_x2 = x2
                bb_y2 = y2
                continue

            bb_x1 = min(bb_x1, x1)
            bb_y1 = min(bb_y1, y1)
            bb_x1 = min(bb_x1, x2)
            bb_y1 = min(bb_y1, y2)
            bb_x2 = max(bb_x2, x1)
            bb_y2 = max(bb_y2, y1)
            bb_x2 = max(bb_x2, x2)
            bb_y2 = max(bb_y2, y2)

        return bb_x1, bb_y1, bb_x2, bb_y2

    def resolve_cover_art(self, caa_id, caa_release_mbid, cover_art_size=500):
        """ Translate a release_mbid into a cover art URL. Return None if unresolvable. """
        if cover_art_size not in (250, 500):
            return None

        return f"https://archive.org/download/mbid-{caa_release_mbid}/mbid-{caa_release_mbid}-{caa_id}_thumb{cover_art_size}.jpg"

    def load_release_caa_ids(self, release_mbids):
        """ Load caa_ids for the given release mbids """
        if len(release_mbids) == 0:
            return {}
        with psycopg2.connect(self.mb_db_connection_str) as conn, \
                conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            return get_caa_ids_for_release_mbids(curs, release_mbids)

    def load_release_group_caa_ids(self, release_group_mbids):
        """ Load caa_ids for the given release group mbids """
        if len(release_group_mbids) == 0:
            return {}
        with psycopg2.connect(self.mb_db_connection_str) as conn, \
                conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            return get_caa_ids_for_release_group_mbids(curs, release_group_mbids)

    def load_images(self, release_mbids, release_group_mbids=[], tile_addrs=None, layout=None, cover_art_size=500):
        """ Given a list of release and release group MBIDs and optional tile addresses, resolve all the cover art design,
            all the cover art to be used and then return the list of images and locations where they should be
            placed. Return an array of dicts containing the image coordinates and the URL of the image. """

        results = {}
        if release_mbids:
            mbids = [mbid for mbid in release_mbids if mbid]
            results = self.load_release_caa_ids(mbids)
        elif release_group_mbids:
            mbids = [mbid for mbid in release_group_mbids if mbid]
            results = self.load_release_group_caa_ids(mbids)

        covers = [
            {
                "entity_mbid": mbid,
                "title": results[mbid]["title"],
                "artist": results[mbid]["artist"],
                "caa_id": results[mbid]["caa_id"],
                "caa_release_mbid": results[mbid]["caa_release_mbid"]
            } for mbid in mbids
        ]
        return self.generate_from_caa_ids(covers, tile_addrs, layout, cover_art_size)

    def generate_from_caa_ids(self, covers, tile_addrs=None, layout=None, cover_art_size=500):
        """ If the caa_ids have already been resolved, use them directly to generate the grid . """
        # See if we're given a layout or a list of tile addresses
        if layout is not None:
            addrs = self.GRID_TILE_DESIGNS[self.dimension][layout]
        elif tile_addrs is None:
            addrs = self.GRID_TILE_DESIGNS[self.dimension][0]
        else:
            addrs = tile_addrs

        # Calculate the bounding boxes for each of the addresses
        tiles = []
        for addr in addrs:
            x1, y1, x2, y2 = self.calculate_bounding_box(addr)
            if x1 is None:
                raise ValueError(f"Invalid address {addr} specified.")
            tiles.append((x1, y1, x2, y2))

        # Now resolve cover art images into URLs and image dimensions
        images = []
        for x1, y1, x2, y2 in tiles:
            while True:
                cover = {}
                try:
                    cover = covers.pop(0)
                    if cover["caa_id"] is None:
                        if self.skip_missing:
                            url = None
                            continue
                        elif self.show_caa_image_for_missing_covers:
                            url = self.CAA_MISSING_IMAGE
                        else:
                            url = None
                    else:
                        url = self.resolve_cover_art(cover["caa_id"], cover["caa_release_mbid"], cover_art_size)

                    break
                except IndexError:
                    if self.show_caa_image_for_missing_covers:
                        url = self.CAA_MISSING_IMAGE
                    else:
                        url = None
                    break

            if url is not None:
                images.append({
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1,
                    "url": url,
                    "entity_mbid": cover.get("entity_mbid"),
                    "title": cover.get("title"),
                    "artist": cover.get("artist"),
                })

        return images

    def download_user_stats(self, entity, user_name, time_range):
        """ Given a user name, a stats entity and a stats time_range, return the stats and total stats count from LB. """

        if time_range not in StatisticsRange.__members__:
            raise ValueError("Invalid date range given.")

        if entity not in ("artists", "releases", "recordings"):
            raise ValueError("Stats entity must be one of artist, release or recording.")

        user = db_user.get_by_mb_id(db_conn, user_name)
        if user is None:
            raise ValueError(f"User {user_name} not found")

        stats = db_stats.get(user["id"], entity, time_range, EntityRecord)
        if stats is None:
            raise ValueError(f"Stats for user {user_name} not found/calculated")

        return stats.data.__root__[:NUMBER_OF_STATS], stats.count

    def create_grid_stats_cover(self, user_name, time_range, layout):
        """ Given a user name, stats time_range and a grid layout, return the array of
            images for the grid and the stats that were downloaded for the grid. """

        releases, _ = self.download_user_stats("releases", user_name, time_range)
        release_mbids = [r.release_mbid for r in releases]
        images = self.load_images(release_mbids, layout=layout)
        if images is None:
            return None, None

        return images, self.time_range_to_english[time_range]

    def create_artist_stats_cover(self, user_name, time_range):
        """ Given a user name and a stats time range, make an artist stats cover. Return
            the artist stats and metadata about this user/stats. The metadata dict contains
            user_name, date, time_range and num_artists. """

        artists, total_count = self.download_user_stats("artists", user_name, time_range)
        metadata = {
            "user_name": user_name,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time_range": self.time_range_to_english[time_range],
            "num_artists": total_count
        }
        return artists, metadata

    def create_release_stats_cover(self, user_name, time_range):
        """ Given a user name and a stats time range, make an release stats cover. Return
            the release stats and metadata about this user/stats. The metadata dict contains:
            user_name, date, time_range and num_releases."""

        releases, total_count = self.download_user_stats("releases", user_name, time_range)
        release_mbids = [r.release_mbid for r in releases]

        images = self.load_images(release_mbids)
        if images is None:
            return None, None, None

        metadata = {
            "user_name": user_name,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time_range": self.time_range_to_english[time_range],
            "num_releases": total_count
        }

        return images, releases, metadata
