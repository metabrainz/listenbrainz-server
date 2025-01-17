import uuid
from typing import List

import psycopg2
import psycopg2.extras
import ujson

import config
from mapping.mb_cache_base import create_metadata_cache, incremental_update_metadata_cache, \
    MusicBrainzEntityMetadataCache
from mapping.mb_metadata_cache import ARTIST_LINK_GIDS_SQL
from mapping.utils import log

MB_ARTIST_METADATA_CACHE_TIMESTAMP_KEY = "mb_artist_metadata_cache_last_update_timestamp"


class MusicBrainzArtistMetadataCache(MusicBrainzEntityMetadataCache):
    """
        This class creates the MB artist metadata cache

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def get_post_process_queries(self):
        return []

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__("mapping.mb_artist_metadata_cache", select_conn, insert_conn, batch_size, unlogged)

    def get_create_table_columns(self):
        # this table is created in local development and tables using admin/timescale/create_tables.sql
        # remember to keep both in sync.
        return [
            ("dirty ", "BOOLEAN DEFAULT FALSE"),
            ("last_updated ", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
            ("artist_mbid ", "UUID NOT NULL"),
            ("artist_data ", "JSONB NOT NULL"),
            ("tag_data ", "JSONB NOT NULL"),
            ("release_group_data ", "JSONB NOT NULL"),
        ]

    def get_insert_queries_test_values(self):
        if config.USE_MINIMAL_DATASET:
            return [[(uuid.UUID(u), ) for u in ('e97f805a-ab48-4c52-855e-07049142113d', 'e95e5009-99b3-42d2-abdd-477967233b08',
                                                '97e69767-5d34-4c97-b36a-f3b2b1ef9dae')]]
        else:
            return [[]]

    def get_index_names(self):
        return [("mb_artist_metadata_cache_idx_artist_mbid", "artist_mbid", True),
                ("mb_artist_metadata_cache_idx_dirty", "dirty", False)]

    def create_json_data(self, row):
        """ Format the data returned into sane JSONB blobs for easy consumption. Return
            recording_data, artist_data, tag_data JSON strings as a tuple.
        """
        artist_mbid = row["artist_mbid"]
        artist = {"name": row["artist_name"], "mbid": row["artist_mbid"]}
        if row["begin_date_year"] is not None:
            artist["begin_year"] = row["begin_date_year"]
        if row["end_date_year"] is not None:
            artist["end_year"] = row["end_date_year"]
        if row["artist_type"] is not None:
            artist["type"] = row["artist_type"]
        if row["gender"] is not None:
            artist["gender"] = row["gender"]
        if row["area"] is not None:
            artist["area"] = row["area"]

        if row["artist_links"]:
            filtered = {}
            for name, url in row["artist_links"]:
                if name is None or url is None:
                    continue
                filtered[name] = url

            if filtered:
                artist["rels"] = filtered

        release_groups = []
        if row["release_groups"]:
            for release_group_mbid, release_group_name, artist_credit_name, year, month, day, type, secondary_types, release_group_artists, caa_id, caa_release_mbid in row["release_groups"]:
                release_group = {
                    "name": release_group_name,
                    "mbid": release_group_mbid,
                    "artist_credit_name": artist_credit_name,
                    "artists": sorted(release_group_artists, key=lambda x: x.pop("position", float('inf')))
                }
                if year is not None:
                    date = str(year)
                    if month is not None:
                        date += "-%02d" % month
                        if day is not None:
                            date += "-%02d" % day
                    release_group["date"] = date

                if type is not None:
                    release_group["type"] = type
                if secondary_types is not None:
                    release_group["secondary_types"] = secondary_types
                if caa_id is not None:
                    release_group["caa_id"] = caa_id
                if caa_release_mbid is not None:
                    release_group["caa_release_mbid"] = caa_release_mbid
                release_groups.append(release_group)

        artist_tags = []
        for tag, count, artist_mbid, genre_mbid in row["artist_tags"] or []:
            tag = {"tag": tag, "count": count, "artist_mbid": artist_mbid}
            if genre_mbid is not None:
                tag["genre_mbid"] = genre_mbid
            artist_tags.append(tag)

        return artist_mbid, ujson.dumps(artist), ujson.dumps({"artist": artist_tags}), ujson.dumps(release_groups)

    def get_metadata_cache_query(self, with_values=False):
        values_cte = ""
        values_join = ""
        if with_values:
            values_cte = "subset (subset_artist_mbid) AS (values %s), "
            values_join = "JOIN subset ON a.gid = subset.subset_artist_mbid"

        query = f"""WITH {values_cte} artist_rels AS (
                            SELECT a.gid AS artist_mbid
                                 , array_agg(distinct(ARRAY[lt.name, url])) AS artist_links
                              FROM musicbrainz.artist a
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
                   ), artist_tags AS (
                            SELECT a.gid AS artist_mbid
                                 , array_agg(jsonb_build_array(t.name, count, a.gid, g.gid)) AS artist_tags
                              FROM musicbrainz.artist a
                              JOIN musicbrainz.artist_tag at
                                ON at.artist = a.id
                              JOIN musicbrainz.tag t
                                ON at.tag = t.id
                         LEFT JOIN musicbrainz.genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                          GROUP BY a.gid
                   ), rg_cover_art AS (
                            SELECT DISTINCT ON(rg.id)
                                   rg.id AS release_group
                                 , caa_rel.gid::TEXT AS caa_release_mbid
                                 , caa.id AS caa_id
                              FROM musicbrainz.artist a
                              JOIN musicbrainz.artist_credit_name acn
                                ON a.id = acn.artist
                              JOIN musicbrainz.release_group rg
                                ON acn.artist_credit = rg.artist_credit
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
                   ), release_group_data AS (
                            SELECT a.gid AS artist_mbid
                                 , rg.gid::TEXT AS release_group_mbid
                                 , rg.name AS release_group_name
                                 , ac.name AS artist_credit_name
                                 , rgca.caa_id AS caa_id
                                 , rgca.caa_release_mbid::TEXT AS caa_release_mbid
                                 , rgm.first_release_date_year AS year
                                 , rgm.first_release_date_month AS month
                                 , rgm.first_release_date_day AS day
                                 , rgpt.name AS type
                                 , array_agg(DISTINCT rgst.name ORDER BY rgst.name)
                                     FILTER (WHERE rgst.name IS NOT NULL)
                                   AS secondary_types
                                 , jsonb_agg(DISTINCT jsonb_build_object(
                                        'artist_mbid', a2.gid::TEXT,
                                        'artist_credit_name', acn2.name,
                                        'join_phrase', acn2.join_phrase,
                                        'position', acn2.position
                                   )) AS release_group_artists
                              FROM musicbrainz.artist a
                              JOIN musicbrainz.artist_credit_name acn
                                ON a.id = acn.artist
                              JOIN musicbrainz.artist_credit ac
                                ON acn.artist_credit = ac.id
                              JOIN musicbrainz.release_group rg
                                ON ac.id = rg.artist_credit
                              JOIN musicbrainz.release_group_meta rgm
                                ON rgm.id = rg.id
                         LEFT JOIN musicbrainz.release_group_primary_type rgpt
                                ON rg.type = rgpt.id
                         LEFT JOIN musicbrainz.release_group_secondary_type_join rgstj
                                ON rgstj.release_group = rg.id
                         LEFT JOIN musicbrainz.release_group_secondary_type rgst
                                ON rgst.id = rgstj.secondary_type
                         LEFT JOIN rg_cover_art rgca
                                ON rgca.release_group = rg.id
                        -- need a second join to artist_credit_name/artist to gather other release group artists' names
                              JOIN musicbrainz.artist_credit_name acn2
                                ON rg.artist_credit = acn2.artist_credit
                              JOIN musicbrainz.artist a2
                                ON acn2.artist = a2.id
                              {values_join}
                          GROUP BY a.gid
                                 , rg.gid
                                 , rg.name
                                 , ac.name
                                 , rgca.caa_id
                                 , rgca.caa_release_mbid
                                 , rgpt.name
                                 , rgm.first_release_date_year
                                 , rgm.first_release_date_month
                                 , rgm.first_release_date_day
                   )
                            SELECT a.gid::TEXT AS artist_mbid
                                 , a.name AS artist_name
                                 , a.begin_date_year
                                 , a.end_date_year
                                 , at.name AS artist_type
                                 , ag.name AS gender
                                 , ar.name AS area
                                 , artist_links
                                 , artist_tags
                                 , array_agg(
                                        jsonb_build_array(
                                            rgd.release_group_mbid,
                                            rgd.release_group_name,
                                            rgd.artist_credit_name, 
                                            rgd.year,
                                            rgd.month,
                                            rgd.day,
                                            rgd.type,
                                            rgd.secondary_types,
                                            rgd.release_group_artists,
                                            rgd.caa_id,
                                            rgd.caa_release_mbid
                                        ) ORDER BY rgd.year, rgd.month, rgd.day
                                   )
                                    -- if the artist has no release groups, left join will cause a NULL row to be
                                    -- added to the array, filter ensures that it is removed
                                    FILTER (WHERE rgd.release_group_mbid IS NOT NULL) AS release_groups
                              FROM musicbrainz.artist a
                         LEFT JOIN musicbrainz.artist_type at
                                ON a.type = at.id
                         LEFT JOIN musicbrainz.gender ag
                                ON a.gender = ag.id
                         LEFT JOIN musicbrainz.area ar
                                ON a.area = ar.id
                         LEFT JOIN artist_rels arl
                                ON arl.artist_mbid = a.gid
                         LEFT JOIN artist_tags ats
                                ON ats.artist_mbid = a.gid
                         LEFT JOIN release_group_data rgd
                                ON rgd.artist_mbid = a.gid
                              {values_join}
                          GROUP BY a.gid
                                 , a.name
                                 , a.begin_date_year
                                 , a.end_date_year
                                 , at.name
                                 , ag.name
                                 , ar.name
                                 , artist_links
                                 , artist_tags
        """
        return query

    def delete_rows(self, artist_mbids: List[uuid.UUID]):
        """Delete recording MBIDs from the mb_artist_metadata_cache table

        Args:
            artist_mbids: a list of Recording MBIDs to delete
        """
        query = f"""
            DELETE FROM {self.table_name}
                  WHERE artist_mbid IN %s
        """
        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        with conn.cursor() as curs:
            curs.execute(query, (tuple(artist_mbids), ))

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
        # |   artist_tags   |  artist tags                   |  artist_tag, genre                 | artist
        # |   artist        |  area, type, gender, life span |  artist, area                      |
        artist_mbids_query = f"""
            SELECT a.gid
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
            SELECT a.gid
              FROM musicbrainz.artist a
              JOIN musicbrainz.area ar
                ON a.area = ar.id
             WHERE ar.last_updated > %(timestamp)s
        UNION
            SELECT a.gid
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
            SELECT a.gid
              FROM musicbrainz.artist a
             WHERE a.last_updated > %(timestamp)s
        """

        # 2. rg_cover_art, release_group_data
        # these CTEs concern release group data and we fetch release and cover art data from these.
        # FIXME: release_group_meta is not considered here because it does not have a last_updated column.
        release_group_mbids_query = """
            WITH release_group_mbids AS (
                SELECT rel.id
                  FROM musicbrainz.release_group rg
                  JOIN musicbrainz.release rel
                    ON rel.release_group = rg.id
             LEFT JOIN cover_art_archive.cover_art caa
                    ON caa.release = rel.id
             LEFT JOIN cover_art_archive.cover_art_type cat
                    ON cat.id = caa.id
                 WHERE rg.last_updated > %(timestamp)s
                    OR (caa.date_uploaded > %(timestamp)s AND (type_id = 1 OR type_id IS NULL))
            )   SELECT a.gid
                  FROM musicbrainz.artist a
                  JOIN musicbrainz.artist_credit_name acn
                    ON acn.artist = a.id
                  JOIN musicbrainz.release_group rg
                    ON rg.artist_credit = acn.artist_credit
                  JOIN release_group_mbids rmb
                    on rg.id = rmb.id
        """

        try:
            with self.select_conn.cursor() as curs:
                self.config_postgres_join_limit(curs)
                artist_mbids = set()

                log("mb artist metadata cache: querying artist mbids to update")
                curs.execute(artist_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    artist_mbids.add(row[0])

                log("mb artist metadata cache: querying release mbids to update")
                curs.execute(release_group_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    artist_mbids.add(row[0])

                return artist_mbids
        except psycopg2.errors.OperationalError as err:
            log("mb artist metadata cache: cannot query rows for update", err)
            return None

    def get_delete_rows_query(self):
        return f"DELETE FROM {self.table_name} WHERE artist_mbid IN %s"


def create_mb_artist_metadata_cache(use_lb_conn: bool):
    """
        Main function for creating the MB metadata cache and its related tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """
    create_metadata_cache(MusicBrainzArtistMetadataCache, MB_ARTIST_METADATA_CACHE_TIMESTAMP_KEY, [], use_lb_conn)


def incremental_update_mb_artist_metadata_cache(use_lb_conn: bool):
    """ Update the MB metadata cache incrementally """
    incremental_update_metadata_cache(MusicBrainzArtistMetadataCache, MB_ARTIST_METADATA_CACHE_TIMESTAMP_KEY, use_lb_conn)

