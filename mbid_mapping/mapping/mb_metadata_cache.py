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
from mapping.canonical_recording_release_redirect import CanonicalRecordingReleaseRedirect
import config


MB_METADATA_CACHE_TIMESTAMP_KEY = "mb_metadata_cache_last_update_timestamp"


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

RECORDING_LINK_GIDS = (
    '628a9658-f54c-4142-b0c0-95f031b544da',
    '59054b12-01ac-43ee-a618-285fd397e461',
    '0fdbe3c6-7700-4a31-ae54-b53f06ae1cfa',
    '234670ce-5f22-4fd0-921b-ef1662695c5d',
    '3b6616c5-88ba-4341-b4ee-81ce1e6d7ebb',
    '92777657-504c-4acb-bd33-51a201bd57e1',
    '45d0cbc5-d65b-4e77-bdfd-8a75207cb5c5',
    '7e41ef12-a124-4324-afdb-fdbae687a89c',
    'b5f3058a-666c-406f-aafb-f9249fc7b122'
)
RECORDING_LINK_GIDS_SQL = ", ".join([f"'{x}'" for x in RECORDING_LINK_GIDS])


class MusicBrainzMetadataCache(BulkInsertTable):
    """
        This class creates the MB metadata cache

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.mb_metadata_cache", mb_conn, lb_conn, batch_size)

    def get_create_table_columns(self):
        # this table is created in local development and tables using admin/timescale/create_tables.sql
        # remember to keep both in sync.
        return [("dirty ",                     "BOOLEAN DEFAULT FALSE"),
                ("recording_mbid ",            "UUID NOT NULL"),
                ("artist_mbids ",              "UUID[] NOT NULL"),
                ("release_mbid ",              "UUID"),
                ("recording_data ",            "JSONB NOT NULL"),
                ("artist_data ",               "JSONB NOT NULL"),
                ("tag_data ",                  "JSONB NOT NULL"),
                ("release_data",               "JSONB NOT NULL")]

    def get_insert_queries_test_values(self):
        if config.USE_MINIMAL_DATASET:
            return [[(uuid.UUID(u),) for u in ('e97f805a-ab48-4c52-855e-07049142113d',
                                               'e95e5009-99b3-42d2-abdd-477967233b08',
                                               '97e69767-5d34-4c97-b36a-f3b2b1ef9dae')]]
        else:
            return [[]]

    def get_insert_queries(self):
        return [("MB", self.get_metadata_cache_query(with_values=config.USE_MINIMAL_DATASET))]

    def pre_insert_queries_db_setup(self, curs):
        self.config_postgres_join_limit(curs)

    def get_post_process_queries(self):
        return ["""
            ALTER TABLE mapping.mb_metadata_cache_tmp
            ADD CONSTRAINT mb_metadata_cache_artist_mbids_check_tmp
                    CHECK ( array_ndims(artist_mbids) = 1 )
        """]

    def get_index_names(self):
        return [("mb_metadata_cache_idx_recording_mbid", "recording_mbid",          True),
                ("mb_metadata_cache_idx_artist_mbids",   "USING gin(artist_mbids)", False),
                ("mb_metadata_cache_idx_dirty",          "dirty",                   False)]

    def process_row(self, row):
        return [("false", *self.create_json_data(row))]

    def process_row_complete(self):
        return []

    def create_json_data(self, row):
        """ Format the data returned into sane JSONB blobs for easy consumption. Return
            recording_data, artist_data, tag_data JSON strings as a tuple.
        """

        release = {}
        if row["release_mbid"] is not None:
            release["mbid"] = row["release_mbid"]
            release["release_group_mbid"] = row["release_group_mbid"]
            release["name"] = row["release_name"]
            release["album_artist_name"] = row["album_artist_name"]
            if row["year"] is not None:
                release["year"] = row["year"]
            if row["caa_id"] is not None:
                release["caa_id"] = row["caa_id"]
            if row["caa_release_mbid"] is not None:
                release["caa_release_mbid"] = row["caa_release_mbid"]

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

        recording_rels = []
        for rel_type, artist_name, artist_mbid, instrument in row["recording_links"] or []:
            rel = {"type": rel_type,
                   "artist_name": artist_name,
                   "artist_mbid": artist_mbid}
            if instrument is not None:
                rel["instrument"] = instrument
            recording_rels.append(rel)

        recording_tags = []
        for tag, count, genre_mbid in row["recording_tags"] or []:
            tag = {"tag": tag, "count": count}
            if genre_mbid is not None:
                tag["genre_mbid"] = genre_mbid
            recording_tags.append(tag)

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

        recording = {
            "name": row["recording_name"],
            "rels": recording_rels
        }
        if row["length"]:
            recording["length"] = row["length"]

        return (row["recording_mbid"],
                artist_mbids,
                row["release_mbid"],
                ujson.dumps(recording),
                ujson.dumps(artist),
                ujson.dumps({"recording": recording_tags, "artist": artist_tags, "release_group": release_group_tags}),
                ujson.dumps(release))

    def get_metadata_cache_query(self, with_values=False):
        values_cte = ""
        values_join = ""
        if with_values:
            values_cte = "subset (subset_recording_mbid) AS (values %s), "
            values_join = "JOIN subset ON r.gid = subset.subset_recording_mbid"

        query = f"""WITH {values_cte} artist_rels AS (
                                SELECT a.gid
                                     , array_agg(distinct(ARRAY[lt.name, url])) AS artist_links
                                  FROM musicbrainz.recording r
                                  JOIN musicbrainz.artist_credit_name acn
                                 USING (artist_credit)
                                -- we cannot directly start as FROM artist a because the values_join JOINs on recording
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
                              GROUP BY a.gid
                   ), recording_rels AS (
                                SELECT r.gid
                                     , array_agg(ARRAY[lt.name, a1.name, a1.gid::TEXT, lat.name]) AS recording_links
                                  FROM musicbrainz.recording r
                                  JOIN musicbrainz.l_artist_recording lar
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
                                 WHERE lt.gid IN ({RECORDING_LINK_GIDS_SQL})
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
                              FROM musicbrainz.recording r
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
                   ), recording_tags AS (
                            SELECT r.gid AS recording_mbid
                                 , array_agg(jsonb_build_array(t.name, count, g.gid)) AS recording_tags
                              FROM musicbrainz.tag t
                              JOIN musicbrainz.recording_tag rt
                                ON rt.tag = t.id
                              JOIN musicbrainz.recording r
                                ON rt.recording = r.id
                         LEFT JOIN musicbrainz.genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                             GROUP BY r.gid
                   ), artist_tags AS (
                            SELECT r.gid AS recording_mbid
                                 , array_agg(jsonb_build_array(t.name, count, a.gid, g.gid)) AS artist_tags
                              FROM musicbrainz.recording r
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
                            SELECT r.gid AS recording_mbid
                                 , array_agg(jsonb_build_array(t.name, count, g.gid)) AS release_group_tags
                              FROM musicbrainz.recording r
                              JOIN mapping.canonical_recording_release_redirect crrr
                                ON r.gid = crrr.recording_mbid
                              JOIN musicbrainz.release rel
                                ON crrr.release_mbid = rel.gid
                              JOIN musicbrainz.release_group_tag rgt
                                ON rgt.release_group = rel.release_group
                              JOIN musicbrainz.tag t
                                ON rgt.tag = t.id
                         LEFT JOIN musicbrainz.genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                          GROUP BY r.gid
                   ), rg_cover_art AS (
                            SELECT DISTINCT ON(rg.id)
                                   rg.id AS release_group
                                 , caa_rel.gid::TEXT AS caa_release_mbid
                                 , caa.id AS caa_id
                              FROM musicbrainz.recording r
                              JOIN mapping.canonical_recording_release_redirect crrr
                                ON r.gid = crrr.recording_mbid
                                -- need to join twice to release, once to get the canonical release group of the recording
                                -- and then to find the preferred cover art release for that release group
                              JOIN musicbrainz.release crrr_rel
                                ON crrr_rel.gid = crrr.release_mbid   
                              JOIN musicbrainz.release_group rg
                                ON rg.id = crrr_rel.release_group
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
                              {values_join}
                             WHERE type_id = 1
                               AND mime_type != 'application/pdf'
                          ORDER BY rg.id
                                 , rgca.release
                                 , re.date_year
                                 , re.date_month
                                 , re.date_day
                                 , caa.ordering
                   ), release_data AS (
                            SELECT r.gid AS recording_mbid
                                 , rel.name
                                 , rac.name AS album_artist_name
                                 , rg.gid AS release_group_mbid
                                 , crrr.release_mbid::TEXT
                                 , rgca.caa_id
                                 , rgca.caa_release_mbid
                              FROM musicbrainz.recording r
                              JOIN mapping.canonical_recording_release_redirect crrr
                                ON r.gid = crrr.recording_mbid
                              JOIN musicbrainz.release rel
                                ON crrr.release_mbid = rel.gid
                              JOIN musicbrainz.artist_credit rac
                                ON rac.id = rel.artist_credit  
                              JOIN musicbrainz.release_group rg
                                ON rel.release_group = rg.id  
                         LEFT JOIN rg_cover_art rgca
                                ON rgca.release_group = rel.release_group
                              {values_join}
                   )
                            SELECT recording_links
                                 , r.name AS recording_name
                                 , r.artist_credit AS artist_credit_id
                                 , ac.name AS artist_credit_name
                                 , artist_data
                                 , artist_tags
                                 , recording_tags
                                 , rd.name AS release_name
                                 , release_group_tags
                                 , rd.release_group_mbid::TEXT
                                 , r.length
                                 , r.gid::TEXT AS recording_mbid
                                 , rd.release_mbid::TEXT
                                 , rd.album_artist_name
                                 , rd.caa_id
                                 , rd.caa_release_mbid
                                 , year
                              FROM musicbrainz.recording r
                              JOIN musicbrainz.artist_credit ac
                                ON r.artist_credit = ac.id
                         LEFT JOIN artist_data ard
                                ON ard.gid = r.gid
                         LEFT JOIN recording_rels rrl
                                ON rrl.gid = r.gid
                         LEFT JOIN recording_tags rt
                                ON rt.recording_mbid = r.gid
                         LEFT JOIN artist_tags ats
                                ON ats.recording_mbid = r.gid
                         LEFT JOIN release_group_tags rts
                                ON rts.recording_mbid = r.gid
                         LEFT JOIN release_data rd
                                ON rd.recording_mbid = r.gid
                         LEFT JOIN mapping.canonical_musicbrainz_data cmb
                                ON cmb.recording_mbid = r.gid
                              {values_join}
                          GROUP BY r.gid
                                 , r.name
                                 , r.artist_credit
                                 , ac.name
                                 , rd.name
                                 , r.length
                                 , recording_links
                                 , recording_tags
                                 , release_group_tags
                                 , rd.release_group_mbid
                                 , artist_data
                                 , artist_tags
                                 , rd.release_mbid
                                 , rd.album_artist_name
                                 , rd.caa_id
                                 , rd.caa_release_mbid
                                 , year"""
        return query

    def delete_rows(self, recording_mbids: List[uuid.UUID]):
        """Delete recording MBIDs from the mb_metadata_cache table

        Args:
            recording_mbids: a list of Recording MBIDs to delete
        """
        query = f"""
            DELETE FROM {self.table_name}
                  WHERE recording_mbid IN %s
        """
        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        with conn.cursor() as curs:
            curs.execute(query, (tuple(recording_mbids),))

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
                 WHERE lt.gid IN ({RECORDING_LINK_GIDS_SQL})
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
                        log("mb metadata update: inserted %d rows. %.1f%%" % (count, 100 * count / total_rows))
                        rows = []

                if rows:
                    batch_recording_mbids = [row[1] for row in rows]
                    self.delete_rows(batch_recording_mbids)
                    insert_rows(lb_curs, self.table_name, rows)
                    conn.commit()

        log("mb metadata update: inserted %d rows. %.1f%%" % (count, 100 * count / total_rows))
        log("mb metadata update: Done!")


def select_metadata_cache_timestamp(conn):
    """ Retrieve the last time the mb metadata cache update was updated """
    query = SQL("SELECT value FROM background_worker_state WHERE key = {key}")\
        .format(key=Literal(MB_METADATA_CACHE_TIMESTAMP_KEY))
    try:
        with conn.cursor() as curs:
            curs.execute(query)
            row = curs.fetchone()
            if row is None:
                log("mb metadata cache: last update timestamp in missing from background worker state")
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


def create_mb_metadata_cache(use_lb_conn: bool):
    """
        Main function for creating the MB metadata cache and its related tables.

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

        can_rel = CanonicalRecordingReleaseRedirect(mb_conn)
        if not can_rel.table_exists():
            log("mb metadata cache: canonical_recording_release_redirect table doesn't exist, run `canonical-data` manage command first with --use-mb-conn option")
            return

        new_timestamp = datetime.now()
        cache = MusicBrainzMetadataCache(mb_conn, lb_conn)
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
