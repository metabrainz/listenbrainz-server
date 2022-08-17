from typing import List
import uuid

import psycopg2
from psycopg2.errors import OperationalError
import psycopg2.extras
import ujson

from mapping.utils import create_schema, insert_rows, log
from mapping.bulk_table import BulkInsertTable
from mapping.canonical_release_redirect import CanonicalReleaseRedirect
import config


class MusicBrainzMetadataCache(BulkInsertTable):
    """
        This class creates the MB metadata cache

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.mb_metadata_cache", mb_conn, lb_conn, batch_size)

    def get_create_table_columns(self):
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
            release["caa_id"] = row["caa_id"]
            release["name"] = row["release_name"]
            if row["year"] is not None:
                release["year"] = row["year"]

        artist = {
            "name": row["artist_credit_name"],
        }
        artists_rels = []
        artist_mbids = []
        for mbid, begin_year, end_year, artist_type, gender, area, rels in row["artist_data"]:
            data = {}
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
            artist_mbids.append(uuid.UUID(artist_mbid))

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
        for tag, count, release_group_mbid, genre_mbid in row["release_group_tags"] or []:
            tag = {"tag": tag,
                   "count": count,
                   "release_group_mbid": release_group_mbid}
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
                list(set(artist_mbids)),
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
                                  FROM recording r
                                  JOIN artist_credit ac
                                    ON r.artist_credit = ac.id
                                  JOIN artist_credit_name acn
                                    ON acn.artist_credit = ac.id
                                  JOIN artist a
                                    ON acn.artist = a.id
                             LEFT JOIN l_artist_url lau
                                    ON lau.entity0 = a.id
                             LEFT JOIN url u
                                    ON lau.entity1 = u.id
                             LEFT JOIN link l
                                    ON lau.link = l.id
                             LEFT JOIN link_type lt
                                    ON l.link_type = lt.id
                                  {values_join}
                                 WHERE (lt.gid IN ('99429741-f3f6-484b-84f8-23af51991770'
                                                  ,'fe33d22f-c3b0-4d68-bd53-a856badf2b15'
                                                  ,'fe33d22f-c3b0-4d68-bd53-a856badf2b15'
                                                  ,'689870a4-a1e4-4912-b17f-7b2664215698'
                                                  ,'93883cf6-e818-4938-990e-75863f8db2d3'
                                                  ,'6f77d54e-1d81-4e1a-9ea5-37947577151b'
                                                  ,'e4d73442-3762-45a8-905c-401da65544ed'
                                                  ,'611b1862-67af-4253-a64f-34adba305d1d'
                                                  ,'f8319a2f-f824-4617-81c8-be6560b3b203'
                                                  ,'34ae77fe-defb-43ea-95d4-63c7540bac78'
                                                  ,'769085a1-c2f7-4c24-a532-2375a77693bd'
                                                  ,'63cc5d1f-f096-4c94-a43f-ecb32ea94161'
                                                  ,'6a540e5b-58c6-4192-b6ba-dbc71ec8fcf0')
                                        OR lt.gid IS NULL)
                              GROUP BY a.gid
                   ), recording_rels AS (
                                SELECT r.gid
                                     , array_agg(ARRAY[lt.name, a1.name, a1.gid::TEXT, lat.name]) AS recording_links
                                  FROM recording r
                             LEFT JOIN l_artist_recording lar
                                    ON lar.entity1 = r.id
                                  JOIN artist a1
                                    ON lar.entity0 = a1.id
                             LEFT JOIN link l
                                    ON lar.link = l.id
                             LEFT JOIN link_type lt
                                    ON l.link_type = lt.id
                             LEFT JOIN link_attribute la
                                    ON la.link = l.id
                             LEFT JOIN link_attribute_type lat
                                    ON la.attribute_type = lat.id
                                  {values_join}
                                 WHERE (lt.gid IN ('628a9658-f54c-4142-b0c0-95f031b544da'
                                                   ,'59054b12-01ac-43ee-a618-285fd397e461'
                                                   ,'0fdbe3c6-7700-4a31-ae54-b53f06ae1cfa'
                                                   ,'234670ce-5f22-4fd0-921b-ef1662695c5d'
                                                   ,'3b6616c5-88ba-4341-b4ee-81ce1e6d7ebb'
                                                   ,'92777657-504c-4acb-bd33-51a201bd57e1'
                                                   ,'45d0cbc5-d65b-4e77-bdfd-8a75207cb5c5'
                                                   ,'7e41ef12-a124-4324-afdb-fdbae687a89c'
                                                   ,'b5f3058a-666c-406f-aafb-f9249fc7b122')
                                       OR lt.gid IS NULL)
                               GROUP BY r.gid
                   ), artist_data AS (
                            SELECT r.gid
                                 , array_agg(jsonb_build_array(a.gid
                                                              ,a.begin_date_year
                                                              ,a.end_date_year
                                                              ,at.name
                                                              ,ag.name
                                                              ,ar.name
                                                              ,artist_links)) AS artist_data
                              FROM recording r
                              JOIN artist_credit ac
                                ON r.artist_credit = ac.id
                              JOIN artist_credit_name acn
                                ON acn.artist_credit = ac.id
                              JOIN artist a
                                ON acn.artist = a.id
                              JOIN artist_type  at
                                ON a.type = at.id
                         LEFT JOIN gender ag
                                ON a.gender = ag.id
                         LEFT JOIN area ar
                                ON a.area = ar.id
                         LEFT JOIN artist_rels arl
                                ON arl.gid = a.gid
                              {values_join}
                          GROUP BY r.gid
                   ), recording_tags AS (
                            SELECT r.gid AS recording_mbid
                                 , array_agg(jsonb_build_array(t.name, count, g.gid)) AS recording_tags
                              FROM musicbrainz.tag t
                              JOIN recording_tag rt
                                ON rt.tag = t.id
                              JOIN recording r
                                ON rt.recording = r.id
                         LEFT JOIN genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                             GROUP BY r.gid
                   ), artist_tags AS (
                            SELECT r.gid AS recording_mbid
                                 , array_agg(jsonb_build_array(t.name, count, a.gid, g.gid)) AS artist_tags
                              FROM recording r
                              JOIN artist_credit ac
                                ON r.artist_credit = ac.id
                              JOIN artist_credit_name acn
                                ON acn.artist_credit = ac.id
                              JOIN artist a
                                ON acn.artist = a.id
                              JOIN artist_tag at
                                ON at.artist = a.id
                              JOIN tag t
                                ON at.tag = t.id
                         LEFT JOIN genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                          GROUP BY r.gid
                   ), release_group_tags AS (
                            SELECT r.gid AS recording_mbid
                                 , rg.gid AS release_group_mbid
                                 , array_agg(jsonb_build_array(t.name, count, rg.gid, g.gid)) AS release_group_tags
                              FROM recording r
                         LEFT JOIN mapping.canonical_release_redirect crr
                                ON r.gid = crr.recording_mbid
                         LEFT JOIN release rel
                                ON crr.release_mbid = rel.gid
                              JOIN release_group rg
                                ON rel.release_group = rg.id
                              JOIN release_group_tag rgt
                                ON rgt.release_group = rel.release_group
                              JOIN tag t
                                ON rgt.tag = t.id
                         LEFT JOIN genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                          GROUP BY r.gid, rg.gid
                   ), release_data AS (
                            SELECT * FROM (
                                    SELECT r.gid AS recording_mbid
                                         , rel.name
                                         , rel.release_group
                                         , crr.release_mbid::TEXT
                                         , caa.id AS caa_id
                                         , row_number() OVER (partition by recording_mbid ORDER BY ordering) AS rownum
                                      FROM recording r
                                 LEFT JOIN mapping.canonical_release_redirect crr
                                        ON r.gid = crr.recording_mbid
                                 LEFT JOIN release rel
                                        ON crr.release_mbid = rel.gid
                                 LEFT JOIN cover_art_archive.cover_art caa
                                        ON caa.release = rel.id
                                 LEFT JOIN cover_art_archive.cover_art_type cat
                                        ON cat.id = caa.id
                                      {values_join}
                                     WHERE type_id = 1
                                        OR type_id IS NULL
                            ) temp where rownum=1
                   )
                            SELECT recording_links
                                 , r.name AS recording_name
                                 , ac.name AS artist_credit_name
                                 , artist_data
                                 , artist_tags
                                 , recording_tags
                                 , rd.name AS release_name
                                 , release_group_tags
                                 , release_group_mbid::TEXT
                                 , r.length
                                 , r.gid::TEXT AS recording_mbid
                                 , rd.release_mbid::TEXT
                                 , rd.caa_id
                                 , year
                              FROM recording r
                              JOIN artist_credit ac
                                ON r.artist_credit = ac.id
                              JOIN artist_credit_name acn
                                ON acn.artist_credit = ac.id
                              JOIN artist a
                                ON acn.artist = a.id
                              JOIN artist_type  at
                                ON a.type = at.id
                              JOIN gender ag
                                ON a.type = ag.id
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
                                 , ac.name
                                 , rd.name
                                 , r.length
                                 , recording_links
                                 , recording_tags
                                 , release_group_tags
                                 , release_group_mbid
                                 , artist_data
                                 , artist_tags
                                 , rd.release_mbid
                                 , caa_id
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

    def mark_rows_as_dirty(self, recording_mbids: List[uuid.UUID], artist_mbids: List[uuid.UUID], release_mbids: List[uuid.UUID]):
        """Mark rows as dirty if the row is for a given recording mbid or if it's by a given artist mbid, or is from a given release mbid"""

        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        try:
            with conn.cursor() as curs:
                query = f"""UPDATE {self.table_name}
                               SET dirty = 't'
                             WHERE recording_mbid IN %s
                                OR %s && artist_mbids
                                OR release_mbid IN %s
                        """
                curs.execute(query, (tuple(recording_mbids), artist_mbids, tuple(release_mbids)))
                conn.commit()

        except psycopg2.errors.OperationalError as err:
            log("mb metadata cache: cannot mark rows as dirty", err)
            conn.rollback()
            raise

    def update_dirty_cache_items(self):
        """Refresh any dirty items in the mb_metadata_cache table.

        This process first looks for all recording MIBDs which are dirty, gets updated metadata for them, and then
        in batches deletes the dirty rows and inserts the updated ones.
        """
        dirty_query = f"""
            SELECT recording_mbid
              FROM {self.table_name}
             WHERE dirty = 't'
        """

        log("mb metadata update: getting dirty items")
        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            with self.mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
                lb_curs.execute(dirty_query)
                recording_mbids = lb_curs.fetchall()

                self.config_postgres_join_limit(mb_curs)

                log("mb metadata update: Running looooong query on dirty items")
                query = self.get_metadata_cache_query(with_values=True)
                values = [(row[0],) for row in recording_mbids]
                psycopg2.extras.execute_values(mb_curs, query, values, page_size=len(values))

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


def create_mb_metadata_cache(use_lb_conn: bool):
    """
        Main function for creating the MB metadata cache and its related tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """

    psycopg2.extras.register_uuid()
    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

        can_rel = CanonicalReleaseRedirect(mb_conn)
        if not can_rel.table_exists():
            log("mb metadata cache: canonical_release_redirect table doesn't exist, run `canonical-data` manage command first with --use-mb-conn option")
            return

        cache = MusicBrainzMetadataCache(mb_conn, lb_conn)
        cache.run()
