from datetime import datetime

from typing import List, Set
import uuid

import psycopg2
from psycopg2.errors import OperationalError
import psycopg2.extras
import ujson
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal

from mapping.utils import insert_rows, log
from mapping.bulk_table import BulkInsertTable
import config


MB_METADATA_CACHE_TIMESTAMP_KEY = "mb_release_group_cache_last_update_timestamp"


ARTIST_LINK_GIDS = (
    '99429741-f3f6-484b-84f8-23af51991770',
    'fe33d22f-c3b0-4d68-bd53-a856badf2b15',
    '689870a4-a1e4-4912-b17f-7b2664215698',
    '93883cf6-e818-4938-990e-75863f8db2d3',
    '6f77d54e-1d81-4e1a-9ea5-37947577151b',
    'e4d73442-3762-45a8-905c-401da65544ed',
    '611b1862-67af-4253-a64f-34adba305d1d',
    'f8319a2f-f824-4617-81c8-be6560b3b203',
    '34ae77fe-defb-43ea-95d4-63c7540bac78',
    '769085a1-c2f7-4c24-a532-2375a77693bd',
    '63cc5d1f-f096-4c94-a43f-ecb32ea94161',
    '6a540e5b-58c6-4192-b6ba-dbc71ec8fcf0'
)
ARTIST_LINK_GIDS_SQL = ", ".join([f"'{x}'" for x in ARTIST_LINK_GIDS])

RELEASE_GROUP_LINK_GIDS = (
    '5e2907db-49ec-4a48-9f11-dfb99d2603ff',
    'b41e7530-cde4-459c-b8c5-dfef08fc8295',
    'cee8e577-6fa6-4d77-abc0-35bce13c570e',
)
RELEASE_GROUP_LINK_GIDS_SQL = ", ".join([f"'{x}'" for x in RELEASE_GROUP_LINK_GIDS])


class MusicBrainzReleaseGroupCache(BulkInsertTable):
    """
        This class creates the MB release group cache

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.mb_release_group_cache", mb_conn, lb_conn, batch_size)
        self.last_updated = None

    def get_create_table_columns(self):
        # this table is created in local development and tables using admin/timescale/create_tables.sql
        # remember to keep both in sync.
        # TODO: DO this.
        return [("dirty ",                     "BOOLEAN DEFAULT FALSE"),
                ("last_updated ",               "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
                ("release_group_mbid ",        "UUID NOT NULL"),
                ("artist_mbids ",              "UUID[] NOT NULL"),
                ("artist_data ",               "JSONB NOT NULL"),
                ("tag_data ",                  "JSONB NOT NULL"),
                ("release_group_data",         "JSONB NOT NULL"),
                ("recording_data",             "JSONB NOT NULL")]

    def get_insert_queries_test_values(self):
        if config.USE_MINIMAL_DATASET:
            return [[(uuid.UUID(u),) for u in ('48140466-cff6-3222-bd55-63c27e43190d',
                                               'c6b36664-7e60-3b3e-a24d-d096c67a11e9',
                                               'f571ba0f-7b96-3607-8b46-a5a60e93f5a5')]]
        else:
            return [[]]

    def get_insert_queries(self):
        return [("MB", self.get_metadata_cache_query(with_values=config.USE_MINIMAL_DATASET))]

    def pre_insert_queries_db_setup(self, curs):
        self.config_postgres_join_limit(curs)
        self.last_updated = datetime.now()

    def get_post_process_queries(self):
        return ["""
            ALTER TABLE mapping.mb_release_group_cache_tmp
            ADD CONSTRAINT mb_release_group_cache_artist_mbids_check_tmp
                    CHECK ( array_ndims(artist_mbids) = 1 )
        """]

    def get_index_names(self):
        return [("mb_release_group_cache_idx_release_group_mbid", "release_group_mbid",      True),
                ("mb_release_group_cache_idx_artist_mbids",       "USING gin(artist_mbids)", False),
                ("mb_release_group_cache_idx_dirty",              "dirty",                   False)]

    def process_row(self, row):
        return [("false", self.last_updated, *self.create_json_data(row))]

    def process_row_complete(self):
        return []

    def create_json_data(self, row):
        """ Format the data returned into sane JSONB blobs for easy consumption. Return
            release_group_data, artist_data, tag_data JSON strings as a tuple.
        """

        artist = {
            "name": row["artist_credit_name"],
            "artist_credit_id": row["artist_credit_id"],
        }
        artists_rels = []
        artist_mbids = []
        for mbid, ac_name, ac_jp, begin_year, end_year, artist_type, gender, area, rels in row["artist_data"]:
            data = {
                "name": ac_name,
                "join_phrase": ac_jp
            }
            if begin_year is not None:
                data["begin_year"] = begin_year
            if end_year is not None:
                data["end_year"] = end_year
            if artist_type is not None:
                data["type"] = artist_type
            if area is not None:
                data["area"] = area
            if rels:
                filtered = {}
                for name, url in rels:
                    if name is None or url is None:
                        continue
                    filtered[name] = url
                if filtered:
                    data["rels"] = filtered
            if artist_type == "Person":
                data["gender"] = gender
            artists_rels.append(data)
            artist_mbids.append(uuid.UUID(mbid))

        artist["artists"] = artists_rels

        release_group_rels = []
        for rel_type, artist_name, artist_mbid, instrument in row["release_group_links"] or []:
            rel = {"type": rel_type,
                   "artist_name": artist_name,
                   "artist_mbid": artist_mbid}
            if instrument is not None:
                rel["instrument"] = instrument
            release_group_rels.append(rel)

        artist_tags = []
        for tag, count, artist_mbid, genre_mbid in row["artist_tags"] or []:
            tag = {"tag": tag,
                   "count": count,
                   "artist_mbid": artist_mbid}
            if genre_mbid is not None:
                tag["genre_mbid"] = genre_mbid
            artist_tags.append(tag)

        release_group_tags = []
        for tag, count, genre_mbid in row["release_group_tags"] or []:
            tag = {
                "tag": tag,
                "count": count,
            }
            if genre_mbid is not None:
                tag["genre_mbid"] = genre_mbid
            release_group_tags.append(tag)

        release_group = {
            "name": row["release_group_name"],
            "date": row["date"],
            "type": row["type"],
            "caa_id": row["caa_id"],
            "caa_release_mbid": row["caa_release_mbid"],
            "rels": release_group_rels
        }

        recordings = []
        for position, name, recording_mbid, length in row["recordings"] or []:
            recordings.append({
                "recording_mbid": recording_mbid,
                "name": name,
                "position": position,
                "length": length
            })

        return (row["release_group_mbid"],
                artist_mbids,
                ujson.dumps(artist),
                ujson.dumps({"artist": artist_tags, "release_group": release_group_tags}),
                ujson.dumps(release_group),
                ujson.dumps({"release_mbid": str(row["recordings_release_mbid"]), "recordings": recordings}))

    def get_metadata_cache_query(self, with_values=False):
        values_cte = ""
        values_join = ""
        if with_values:
            values_cte = "subset (subset_release_group_mbid) AS (values %s), "
            values_join = "JOIN subset ON r.gid = subset.subset_release_group_mbid"

        query = f"""WITH {values_cte} artist_rels AS (
                                SELECT a.gid
                                     , array_agg(distinct(ARRAY[lt.name, url])) AS artist_links
                                  FROM musicbrainz.release_group r
                                  JOIN musicbrainz.artist_credit_name acn
                                 USING (artist_credit)
                                -- we cannot directly start as FROM artist a because the values_join JOINs on release_group
                                  JOIN musicbrainz.artist a
                                    ON acn.artist = a.id
                                  JOIN musicbrainz.l_artist_url lau
                                    ON lau.entity0 = a.id
                                  JOIN musicbrainz.url u
                                    ON lau.entity1 = u.id
                                  JOIN musicbrainz.link l
                                    ON lau.link = l.id
                                  JOIN musicbrainz.link_type lt
                                    ON l.link_type = lt.id
                                  {values_join}
                                 WHERE lt.gid IN ({ARTIST_LINK_GIDS_SQL})
                                   AND NOT l.ended
                              GROUP BY a.gid
                   ), release_group_rels AS (
                                SELECT r.gid
                                     , array_agg(ARRAY[lt.name, a1.name, a1.gid::TEXT, lat.name]) AS release_group_links
                                  FROM musicbrainz.release_group r
                                  JOIN musicbrainz.l_artist_release_group lar
                                    ON lar.entity1 = r.id
                                  JOIN musicbrainz.artist a1
                                    ON lar.entity0 = a1.id
                                  JOIN musicbrainz.link l
                                    ON lar.link = l.id
                                  JOIN musicbrainz.link_type lt
                                    ON l.link_type = lt.id
                             LEFT JOIN musicbrainz.link_attribute la
                                    ON la.link = l.id
                             LEFT JOIN musicbrainz.link_attribute_type lat
                                    ON la.attribute_type = lat.id
                                  {values_join}
                                 WHERE lt.gid IN ({RELEASE_GROUP_LINK_GIDS_SQL})
                                   AND NOT l.ended
                               GROUP BY r.gid
                   ), artist_data AS (
                            SELECT r.gid
                                 , jsonb_agg(
                                    jsonb_build_array(
                                        a.gid
                                      , acn.name
                                      , acn.join_phrase
                                      , a.begin_date_year
                                      , a.end_date_year
                                      , at.name
                                      , ag.name
                                      , ar.name
                                      , artist_links
                                    )
                                    ORDER BY acn.position
                                   ) AS artist_data
                              FROM musicbrainz.release_group r
                              JOIN musicbrainz.artist_credit_name acn
                             USING (artist_credit)
                              JOIN musicbrainz.artist a
                                ON acn.artist = a.id
                         LEFT JOIN musicbrainz.artist_type at
                                ON a.type = at.id
                         LEFT JOIN musicbrainz.gender ag
                                ON a.gender = ag.id
                         LEFT JOIN musicbrainz.area ar
                                ON a.area = ar.id
                         LEFT JOIN artist_rels arl
                                ON arl.gid = a.gid
                              {values_join}
                          GROUP BY r.gid
                   ), artist_tags AS (
                            SELECT r.gid AS release_group_mbid
                                 , array_agg(jsonb_build_array(t.name, count, a.gid, g.gid)) AS artist_tags
                              FROM musicbrainz.release_group r
                              JOIN musicbrainz.artist_credit_name acn
                             USING (artist_credit)
                              JOIN musicbrainz.artist a
                                ON acn.artist = a.id
                              JOIN musicbrainz.artist_tag at
                                ON at.artist = a.id
                              JOIN musicbrainz.tag t
                                ON at.tag = t.id
                         LEFT JOIN musicbrainz.genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                          GROUP BY r.gid
                   ), release_group_tags AS (
                            SELECT r.gid AS release_group_mbid
                                 , array_agg(jsonb_build_array(t.name, count, g.gid)) AS release_group_tags
                              FROM musicbrainz.release_group r
                              JOIN musicbrainz.release_group_tag rgt
                                ON r.id = rgt.release_group
                              JOIN musicbrainz.tag t
                                ON rgt.tag = t.id
                         LEFT JOIN musicbrainz.genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                          GROUP BY r.gid
                   ), rg_cover_art AS (
                            SELECT DISTINCT ON(r.id)
                                   r.id AS release_group
                                 , caa_rel.gid::TEXT AS caa_release_mbid
                                 , caa.id AS caa_id
                              FROM musicbrainz.release_group r
                              JOIN musicbrainz.release caa_rel
                                ON r.id = caa_rel.release_group
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
                              {values_join}
                             WHERE type_id = 1
                               AND mime_type != 'application/pdf'
                          ORDER BY r.id
                                 , rgca.release
                                 , re.date_year
                                 , re.date_month
                                 , re.date_day
                                 , caa.ordering
                   ), canonical_release_selection AS (
                            SELECT DISTINCT ON (rg.gid)
                                   rg.gid AS release_group_mbid
                                 , rel.id AS release_id
                              FROM musicbrainz.release_group rg
                              JOIN musicbrainz.release rel
                                ON rel.release_group = rg.id
                              JOIN mapping.canonical_release crl
                                ON rel.id = crl.release
                              {values_join}
                          ORDER BY rg.gid
                                 , crl.id
                   ), recording_data AS (
                           SELECT release_group_mbid
                                , rel.gid AS recordings_release_mbid
                                , array_agg(jsonb_build_array(t.position, r.name, r.gid::TEXT, r.length) ORDER BY t.position) AS recordings
                             FROM canonical_release_selection crs
                             JOIN musicbrainz.release rel
                               ON rel.id = crs.release_id
                             JOIN musicbrainz.medium m
                               ON m.release = rel.id
                             JOIN musicbrainz.track t
                               ON t.medium = m.id
                             JOIN musicbrainz.recording r
                               ON r.id = t.recording
                              {values_join}
                         GROUP BY release_group_mbid
                                , rel.gid
                   )
                            SELECT release_group_links
                                 , r.name AS release_group_name
                                 , r.artist_credit AS artist_credit_id
                                 , ac.name AS artist_credit_name
                                 , artist_data
                                 , artist_tags
                                 , release_group_tags
                                 , r.gid::TEXT AS release_group_mbid
                                 , rgca.caa_id
                                 , rgca.caa_release_mbid
                                 , rgpt.name AS type
                                 , (rgm.first_release_date_year::TEXT || '-' ||
                                    LPAD(rgm.first_release_date_month::TEXT, 2, '0') || '-' ||
                                    LPAD(rgm.first_release_date_day::TEXT, 2, '0')) AS date
                                 , rec_data.recordings
                                 , rec_data.recordings_release_mbid
                              FROM musicbrainz.release_group r
                              JOIN musicbrainz.artist_credit ac
                                ON r.artist_credit = ac.id
                         LEFT JOIN musicbrainz.release_group_primary_type rgpt
                                ON r.type = rgpt.id
                         LEFT JOIN musicbrainz.release_group_meta rgm
                                ON rgm.id = r.id
                         LEFT JOIN artist_data ard
                                ON ard.gid = r.gid
                         LEFT JOIN release_group_rels rrl
                                ON rrl.gid = r.gid
                         LEFT JOIN release_group_tags rt
                                ON rt.release_group_mbid = r.gid
                         LEFT JOIN artist_tags ats
                                ON ats.release_group_mbid = r.gid
                         LEFT JOIN rg_cover_art rgca
                                ON rgca.release_group = r.id
                         LEFT JOIN recording_data rec_data
                                ON rec_data.release_group_mbid = r.gid
                              {values_join}
                          GROUP BY r.gid
                                 , r.name
                                 , r.artist_credit
                                 , ac.name
                                 , rgpt.name
                                 , rgm.first_release_date_year
                                 , rgm.first_release_date_month
                                 , rgm.first_release_date_day
                                 , release_group_links
                                 , release_group_tags
                                 , artist_data
                                 , artist_tags
                                 , rgca.caa_id
                                 , rgca.caa_release_mbid
                                 , rec_data.recordings
                                 , rec_data.recordings_release_mbid
                   """
        return query

    def delete_rows(self, release_group_mbids: List[uuid.UUID]):
        """Delete release_group MBIDs from the mb_metadata_cache table

        Args:
            release_group_mbids: a list of Recording MBIDs to delete
        """
        query = f"""
            DELETE FROM {self.table_name}
                  WHERE release_group_mbid IN %s
        """
        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        with conn.cursor() as curs:
            curs.execute(query, (tuple(release_group_mbids),))

    def config_postgres_join_limit(self, curs):
        """
        Because of the size of query we need to hint to postgres that it should continue to
        reorder JOINs in an optimal order. Without these settings, PG will take minutes to
        execute the metadata cache query for even for 3-4 mbids. With these settings,
        the query planning time increases by few milliseconds but the query running time
        becomes instantaneous.
        """
        curs.execute('SET geqo = off')
        curs.execute('SET geqo_threshold = 20')
        curs.execute('SET from_collapse_limit = 15')
        curs.execute('SET join_collapse_limit = 15')

    # TODO Update this
    def query_last_updated_items(self, timestamp):
        # there queries mirror the structure and logic of the main cache building queries
        # note that the tags queries in any of these omit the count > 0 clause because possible removal
        # of a tag is also a change.
        # the last_updated considered and last_updated ignored columns below together list all the last_updated
        # columns a given CTE touches. any other tables touched by a given CTE do not have a last_updated column.

        # these queries only take updates and deletions into consideration, not deletes. because the deleted data
        # has already been removed from the database. a periodic rebuild of the entire cache removes deleted rows

        # 1. artist_rels, artist_data, artist_tags, artist
        # these CTEs and tables concern artist data and we fetch artist mbids from these. all of the CTEs touch
        # artist table but do not consider its last_updated column because that is done separately at end. further,
        # the queries here have been simplified to not include recording tables as that will be considered by a
        # separate query.
        #
        # |   CTE / table   |       purpose                  |  last_updated considered           | last_updated ignored
        # |   artist_rels   |  artist - url links            |  link relationship related and url | artist
        # |   artist_data   |  life span, area, type, gender |  area                              | artist
        # |   artist_tags   |  artist tags                   |  recording_tag, genre              | artist
        # |   artist        |                                |  artist                            |
        artist_mbids_query = f"""
        WITH artist_mbids(id) AS (
            SELECT a.id
              FROM musicbrainz.artist a
              JOIN musicbrainz.l_artist_url lau
                ON lau.entity0 = a.id
              JOIN musicbrainz.url u
                ON lau.entity1 = u.id
              JOIN musicbrainz.link l
                ON lau.link = l.id
              JOIN musicbrainz.link_type lt
                ON l.link_type = lt.id
             WHERE lt.gid IN ({ARTIST_LINK_GIDS_SQL})
                   AND (
                        lau.last_updated > %(timestamp)s
                     OR   u.last_updated > %(timestamp)s
                     OR  lt.last_updated > %(timestamp)s
                   )
        UNION
            SELECT a.id
              FROM musicbrainz.artist a
              JOIN musicbrainz.area ar
                ON a.area = ar.id
             WHERE ar.last_updated > %(timestamp)s
        UNION
            SELECT a.id
              FROM musicbrainz.artist a
              JOIN musicbrainz.artist_tag at
                ON at.artist = a.id
              JOIN musicbrainz.tag t
                ON at.tag = t.id
         LEFT JOIN musicbrainz.genre g
                ON t.name = g.name
             WHERE at.last_updated > %(timestamp)s
                OR  g.last_updated > %(timestamp)s
        UNION
            SELECT a.id
              FROM musicbrainz.artist a
             WHERE a.last_updated > %(timestamp)s
        ) SELECT r.gid
            FROM musicbrainz.recording r
            JOIN musicbrainz.artist_credit_name acn
           USING (artist_credit)
            JOIN artist_mbids am
              ON acn.artist = am.id
        """

        # 2. recording_rels, recording_tags, recording
        # these CTEs concern recording data and we fetch recording_mbids from these. the CTEs do not join to artist
        # table because that has been considered earlier.
        #
        # |   CTE / table    |         purpose               |  last_updated considered           | last_updated ignored
        # |   recording_rels |   artist - recording links    |  link relationship related and url | recording, artist
        # |   recording_tags |   recording tags              |  recording_tag, genre              | recording
        # |   recording      |                               |  recording                         |
        recording_mbids_query = f"""
                SELECT r.gid
                  FROM musicbrainz.recording r
                  JOIN musicbrainz.l_artist_recording lar
                    ON lar.entity1 = r.id
                  JOIN musicbrainz.link l
                    ON lar.link = l.id
                  JOIN musicbrainz.link_type lt
                    ON l.link_type = lt.id
                  JOIN musicbrainz.link_attribute la
                    ON la.link = l.id
                  JOIN musicbrainz.link_attribute_type lat
                    ON la.attribute_type = lat.id
                 WHERE lt.gid IN ({RELEASE_GROUP_LINK_GIDS_SQL})
                   AND (
                         lar.last_updated > %(timestamp)s
                      OR  lt.last_updated > %(timestamp)s
                      OR lat.last_updated > %(timestamp)s
                   )
            UNION
                SELECT r.gid
                  FROM musicbrainz.tag t
                  JOIN musicbrainz.recording_tag rt
                    ON rt.tag = t.id
                  JOIN musicbrainz.recording r
                    ON rt.recording = r.id
             LEFT JOIN musicbrainz.genre g
                    ON t.name = g.name
                 WHERE rt.last_updated > %(timestamp)s
                    OR  g.last_updated > %(timestamp)s
            UNION
                SELECT r.gid
                  FROM musicbrainz.recording r
                 WHERE r.last_updated > %(timestamp)s
        """

        # 3. release_group_tags, release_data
        # these CTEs concern release data and we fetch release and cover art data from these. the CTEs do not join to
        # recording table because that has been considered earlier.
        #
        # |   CTE / table        |        purpose             |  last_updated considered    | last_updated ignored
        # |   release_group_tags |  release group level tags  |  release_group_tag, genre   | release, release_group
        # |   release_data       |  release name, cover art   |                             | release, release_group
        # |   release            |                            |  release, release_group     |
        release_mbids_query = """
            WITH release_mbids(id) AS (
                SELECT rel.id
                  FROM mapping.canonical_recording_release_redirect crrr
                  JOIN musicbrainz.release rel
                    ON crrr.release_mbid = rel.gid
                  JOIN musicbrainz.release_group rg
                    ON rel.release_group = rg.id
                  JOIN musicbrainz.release_group_tag rgt
                    ON rgt.release_group = rel.release_group
                  JOIN musicbrainz.tag t
                    ON rgt.tag = t.id
             LEFT JOIN musicbrainz.genre g
                    ON t.name = g.name
                 WHERE rgt.last_updated > %(timestamp)s
                    OR   g.last_updated > %(timestamp)s
            UNION
                SELECT rel.id
                  FROM mapping.canonical_recording_release_redirect crrr
                  JOIN musicbrainz.release rel
                    ON crrr.release_mbid = rel.gid
                  JOIN musicbrainz.release_group rg
                    ON rel.release_group = rg.id
             LEFT JOIN cover_art_archive.cover_art caa
                    ON caa.release = rel.id
             LEFT JOIN cover_art_archive.cover_art_type cat
                    ON cat.id = caa.id
                 WHERE  rel.last_updated > %(timestamp)s
                    OR   rg.last_updated > %(timestamp)s
                    OR (caa.date_uploaded > %(timestamp)s AND (type_id = 1 OR type_id IS NULL))
            ) SELECT r.gid
                FROM musicbrainz.recording r
                JOIN musicbrainz.track t
                  ON t.recording = r.id
                JOIN musicbrainz.medium m
                  ON m.id = t.medium
                JOIN release_mbids rm
                  ON rm.id = m.release
        """

        try:
            with self.mb_conn.cursor() as curs:
                self.config_postgres_join_limit(curs)
                recording_mbids = set()

                log("mb metadata cache: querying recording mbids to update")
                curs.execute(recording_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    recording_mbids.add(row[0])

                log("mb metadata cache: querying artist mbids to update")
                curs.execute(artist_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    recording_mbids.add(row[0])

                log("mb metadata cache: querying release mbids to update")
                curs.execute(release_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    recording_mbids.add(row[0])

                return recording_mbids
        except psycopg2.errors.OperationalError as err:
            log("mb metadata cache: cannot query rows for update", err)
            return None

    def update_dirty_cache_items(self, recording_mbids: Set[uuid.UUID]):
        """Refresh any dirty items in the mb_metadata_cache table.

        This process first looks for all recording MIBDs which are dirty, gets updated metadata for them, and then
        in batches deletes the dirty rows and inserts the updated ones.
        """
        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            with self.mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
                self.config_postgres_join_limit(mb_curs)

                log("mb metadata update: Running looooong query on dirty items")
                query = self.get_metadata_cache_query(with_values=True)
                values = [(mbid,) for mbid in recording_mbids]
                execute_values(mb_curs, query, values, page_size=len(values))

                rows = []
                count = 0
                total_rows = len(recording_mbids)
                for row in mb_curs:
                    count += 1
                    data = self.create_json_data(row)
                    rows.append(("false", *data))
                    if len(rows) >= self.batch_size:
                        batch_recording_mbids = [row[1] for row in rows]
                        self.delete_rows(batch_recording_mbids)
                        insert_rows(lb_curs, self.table_name, rows)
                        conn.commit()
                        rows = []

                if rows:
                    batch_recording_mbids = [row[1] for row in rows]
                    self.delete_rows(batch_recording_mbids)
                    insert_rows(lb_curs, self.table_name, rows)
                    conn.commit()

        log("mb metadata update: inserted %d rows. %.1f%%" % (count, 100 * count / total_rows))
        log("mb metadata update: Done!")


def select_metadata_cache_timestamp(conn):
    """ Retrieve the last time the mb release_group cache update was updated """
    query = SQL("SELECT value FROM background_worker_state WHERE key = {key}")\
        .format(key=Literal(MB_RELEASE_GROUP_CACHE_TIMESTAMP_KEY))
    try:
        with conn.cursor() as curs:
            curs.execute(query)
            row = curs.fetchone()
            if row is None:
                log("mb release_group cache: last update timestamp in missing from background worker state")
                return None
            return datetime.fromisoformat(row[0])
    except psycopg2.errors.UndefinedTable:
        log("mb metadata cache: background_worker_state table is missing, create the table to record update timestamps")
        return None


def update_metadata_cache_timestamp(conn, ts: datetime):
    """ Update the timestamp of metadata creation in database. The incremental update process will read this
     timestamp next time it runs and only update cache for rows updated since then in MB database. """
    query = SQL("UPDATE background_worker_state SET value = %s WHERE key = {key}") \
        .format(key=Literal(MB_METADATA_CACHE_TIMESTAMP_KEY))
    with conn.cursor() as curs:
        curs.execute(query, (ts.isoformat(),))
    conn.commit()


# TODO ^^ not updated


def create_mb_release_group_cache(use_lb_conn: bool):
    """
        Main function for creating the MB release group cache and its related tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """
    psycopg2.extras.register_uuid()

    if use_lb_conn:
        mb_uri = config.MB_DATABASE_STANDBY_URI or config.MBID_MAPPING_DATABASE_URI
    else:
        mb_uri = config.MBID_MAPPING_DATABASE_URI

    with psycopg2.connect(mb_uri) as mb_conn:
        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

        new_timestamp = datetime.now()
        cache = MusicBrainzReleaseGroupCache(mb_conn, lb_conn)
        cache.run()
        update_metadata_cache_timestamp(lb_conn or mb_conn, new_timestamp)


def incremental_update_mb_metadata_cache(use_lb_conn: bool):
    """ Update the MB metadata cache incrementally """
    psycopg2.extras.register_uuid()

    if use_lb_conn:
        mb_uri = config.MB_DATABASE_STANDBY_URI or config.MBID_MAPPING_DATABASE_URI
    else:
        mb_uri = config.MBID_MAPPING_DATABASE_URI

    with psycopg2.connect(mb_uri) as mb_conn:
        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

        cache = MusicBrainzMetadataCache(mb_conn, lb_conn)
        if not cache.table_exists():
            log("mb metadata cache: table does not exist, first create the table normally")
            return

        log("mb metadata cache: starting incremental update")

        timestamp = select_metadata_cache_timestamp(lb_conn or mb_conn)
        log(f"mb metadata cache: last update timestamp - {timestamp}")
        if not timestamp:
            return

        new_timestamp = datetime.now()
        recording_mbids = cache.query_last_updated_items(timestamp)
        cache.update_dirty_cache_items(recording_mbids)

        if len(recording_mbids) == 0:
            log("mb metadata cache: no recording mbids found to update")
            return

        update_metadata_cache_timestamp(lb_conn or mb_conn, new_timestamp)

        log("mb metadata cache: incremental update completed")


def cleanup_mbid_mapping_table():
    """ Find msids which are mapped to mbids that are now absent from mb_metadata_cache
     because those have been merged (redirects) or deleted from MB and flag such msids
     to be re-mapped by the mbid mapping writer."""
    query = """
        UPDATE mbid_mapping mm
           SET last_updated = 'epoch'
         WHERE match_type != 'no_match'
           AND NOT EXISTS(
                SELECT 1
                  FROM mapping.mb_metadata_cache mbc
                 WHERE mbc.recording_mbid = mm.recording_mbid
               )
    """
    with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as lb_conn, lb_conn.cursor() as lb_curs:
        lb_curs.execute(query)
        log(f"mbid mapping: invalidated {lb_curs.rowcount} rows")
        lb_conn.commit()