import uuid
from datetime import datetime, timezone
from typing import List, Set

import psycopg2
import psycopg2.extras
import ujson

import config
from mapping.mb_cache_base import (
    create_metadata_cache,
    incremental_update_metadata_cache,
    MusicBrainzEntityMetadataCache,
)
from mapping.bulk_table import BulkInsertTable
from mapping.utils import insert_rows, log

MB_EVENT_METADATA_CACHE_TIMESTAMP_KEY = "mb_event_metadata_cache_last_update_timestamp"

ARTIST_EVENT_LINK_GIDS = (
    "936c7c95-3156-3889-a062-8a0cd57f8946",  # main performer
    "492a850e-97eb-306a-a85e-4b6d98527796",  # support act
    "292df906-98a6-307e-86e8-df01a579a321",  # guest performer
)
ARTIST_EVENT_LINK_GIDS_SQL = ", ".join([f"'{x}'" for x in ARTIST_EVENT_LINK_GIDS])

EVENT_URL_LINK_GIDS = (
    "c26808b0-4e67-31a7-a587-913720dfb3f3",  # official homepage
    "68f5fcaa-b58c-3bfe-9b7c-75c2b56e839a",  # social network
    "125afc57-4d33-3b63-ab41-848a3a18d3a6",  # songkick
    "b022d060-e6a8-340f-8c73-6b21b1d090b9",  # wikidata
    "08a982f7-d754-39b2-8315-d7cae474c641",  # wikipedia
    "fea46163-dc45-3af9-917e-1798f325d21a",  # youtube
)
EVENT_URL_LINK_GIDS_SQL = ", ".join([f"'{x}'" for x in EVENT_URL_LINK_GIDS])

EVENT_PLACE_LINK_GID = "e2c6f697-07dc-38b1-be0b-83d740165532"

# falls back to area if no place
AREA_EVENT_LINK_GID = "542f8484-8bc7-3ce5-a022-747850b2b928"


class MusicBrainzEventArtistCache(BulkInsertTable):
    """
        This class creates the artist-event edge cache, driven by the
        primary MusicBrainzEventMetadataCache table.
    """

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__(
            "mapping.mb_event_artist_cache",
            select_conn,
            insert_conn,
            batch_size,
            unlogged,
        )

    def get_create_table_columns(self):
        # this table is created in local development and tests using admin/timescale/create_tables.sql.
        # remember to keep both in sync.
        return [
            ("event_mbid ", "UUID NOT NULL"),
            ("event_id ", "INTEGER NOT NULL"),
            ("artist_mbid ", "UUID NOT NULL"),
            ("artist_id ", "INTEGER NOT NULL"),
            ("link_id ", "INTEGER NOT NULL"),
            ("link_type_gid ", "UUID NOT NULL"),
            ("link_type_name ", "TEXT NOT NULL"),
            ("relationship_data ", "JSONB NOT NULL DEFAULT '{}'::jsonb"),
            ("last_updated ", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
        ]

    def get_insert_queries(self):
        return []

    def get_insert_queries_test_values(self):
        return []

    def get_post_process_queries(self):
        return []

    def get_index_names(self):
        return [
            (
                "mb_event_artist_cache_idx_artist_id_event_id",
                "artist_id, event_id",
                False,
            ),
            ("mb_event_artist_cache_idx_artist_mbid", "artist_mbid", False),
            ("mb_event_artist_cache_idx_event_id", "event_id", False),
            ("mb_event_artist_cache_idx_link_type_gid", "link_type_gid", False),
            ("mb_event_artist_cache_pkey", "event_id, artist_id, link_id", True),
        ]

    def process_row(self, row):
        return []

    def process_row_complete(self):
        return []


class MusicBrainzEventMetadataCache(MusicBrainzEntityMetadataCache):
    """
        This class creates the MB event metadata cache and its associated
        artist-event edge table.
    """

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__(
            "mapping.mb_event_cache", select_conn, insert_conn, batch_size, unlogged
        )
        self.artist_cache = MusicBrainzEventArtistCache(
            select_conn, insert_conn, batch_size, unlogged
        )
        self.add_additional_bulk_table(self.artist_cache)

    def get_create_table_columns(self):
        # this table is created in local development and tests using admin/timescale/create_tables.sql.
        # remember to keep both in sync.
        return [
            ("dirty ", "BOOLEAN DEFAULT FALSE"),
            ("last_updated ", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
            ("event_mbid ", "UUID NOT NULL"),
            ("event_id ", "INTEGER NOT NULL"),
            ("event_name ", "TEXT NOT NULL"),
            ("begin_date_year ", "SMALLINT"),
            ("begin_date_month ", "SMALLINT"),
            ("begin_date_day ", "SMALLINT"),
            ("end_date_year ", "SMALLINT"),
            ("end_date_month ", "SMALLINT"),
            ("end_date_day ", "SMALLINT"),
            ("event_time ", "TIMESTAMPTZ"),
            ("cancelled ", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("ended ", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("event_type_gid ", "UUID"),
            ("event_art_presence ", "TEXT NOT NULL DEFAULT 'absent'"),
            ("place_mbid ", "UUID"),
            ("place_name ", "TEXT"),
            ("area_mbid ", "UUID"),
            ("rating ", "SMALLINT"),
            ("rating_count ", "INTEGER"),
            ("event_data ", "JSONB NOT NULL DEFAULT '{}'::jsonb"),
        ]

    def get_insert_queries_test_values(self):
        if config.USE_MINIMAL_DATASET:
            return [
                [
                    (uuid.UUID(u),)
                    for u in (
                        "1bfefc05-dbbb-4aaa-8d1b-6ddc00114eb7",
                        "9c81bb52-87be-48d5-a7cb-da91f6c94b5e",
                        "a777f05b-a934-4648-9a5c-60284b588c0e",
                        "4996ec02-a2c6-405d-99b7-c545e3ad040a"
                    )
                ]
            ]
        else:
            return [[]]

    def get_post_process_queries(self):
        return []

    def get_index_names(self):
        return [
            ("mb_event_cache_idx_event_mbid", "event_mbid", True),
            ("mb_event_cache_idx_event_id", "event_id", True),
            (
                "mb_event_cache_idx_date",
                "begin_date_year, begin_date_month, begin_date_day",
                False,
            ),
            ("mb_event_cache_idx_dirty", "dirty", False),
        ]

    def process_row(self, row):
        event_row = ("false", self.last_updated, *self.create_json_data(row))
        artist_rows = self._create_artist_edge_rows(row)
        return {
            "mapping.mb_event_cache": [event_row],
            "mapping.mb_event_artist_cache": artist_rows,
        }

    def _assemble_event_time(self, row):
        """ Combine event.time with begin_date into a full timestamp.
            Returns None if either part is missing. Assuming UTC.
        """
        event_time_raw = row["event_time_raw"]
        if event_time_raw is None:
            return None

        year = row["begin_date_year"]
        month = row["begin_date_month"]
        day = row["begin_date_day"]
        if year is None or month is None or day is None:
            return None

        try:
            return datetime(
                year,
                month,
                day,
                event_time_raw.hour,
                event_time_raw.minute,
                event_time_raw.second,
                tzinfo=timezone.utc,
            )
        except (ValueError, AttributeError):
            return None

    def create_json_data(self, row):
        event_mbid = row["event_mbid"]
        event_time = self._assemble_event_time(row)

        event_data = {}

        if row["event_type_name"] is not None:
            event_data["type"] = row["event_type_name"]

        if row["disambiguation"]:
            event_data["disambiguation"] = row["disambiguation"]

        if row["setlist"]:
            event_data["setlist"] = row["setlist"]

        if row["area_name"]:
            event_data["area_name"] = row["area_name"]

        if row["event_links"]:
            filtered = {}
            for name, url in row["event_links"]:
                if name is None or url is None:
                    continue
                filtered[name] = url
            if filtered:
                event_data["rels"] = filtered

        event_tags = []
        for tag, count, genre_mbid in row["event_tags"] or []:
            tag_entry = {"tag": tag, "count": count}
            if genre_mbid is not None:
                tag_entry["genre_mbid"] = genre_mbid
            event_tags.append(tag_entry)
        if event_tags:
            event_data["tags"] = event_tags

        if row["event_art_id"] is not None:
            event_data["event_art_id"] = row["event_art_id"]

        return (
            event_mbid,
            row["event_id"],
            row["event_name"],
            row["begin_date_year"],
            row["begin_date_month"],
            row["begin_date_day"],
            row["end_date_year"],
            row["end_date_month"],
            row["end_date_day"],
            event_time,
            row["cancelled"],
            row["ended"],
            row["event_type_gid"],
            row["event_art_presence"] or "absent",
            row["place_mbid"],
            row["place_name"],
            row["area_mbid"],
            row["rating"],
            row["rating_count"],
            ujson.dumps(event_data),
        )

    def _create_artist_edge_rows(self, row):
        rows = []
        if not row["artist_edges"]:
            return rows

        for edge in row["artist_edges"]:
            artist_mbid = edge[0]
            artist_id = edge[1]
            link_id = edge[2]
            link_type_gid = edge[3]
            link_type_name = edge[4]
            entity0_credit = edge[5]

            relationship_data = {}
            if entity0_credit:
                relationship_data["credited_as"] = entity0_credit

            rows.append(
                (
                    row["event_mbid"],
                    row["event_id"],
                    artist_mbid,
                    artist_id,
                    link_id,
                    link_type_gid,
                    link_type_name,
                    ujson.dumps(relationship_data),
                    self.last_updated,
                )
            )

        return rows

    def get_metadata_cache_query(self, with_values=False):
        values_cte = ""
        values_join = ""
        if with_values:
            values_cte = "subset (subset_event_mbid) AS (values %s), "
            values_join = "JOIN subset ON e.gid = subset.subset_event_mbid"

        query = f"""WITH {values_cte} event_url_rels AS (
                            SELECT e.gid AS event_mbid
                                 , array_agg(DISTINCT ARRAY[lt.name, url]) AS event_links
                              FROM musicbrainz.event e
                              JOIN musicbrainz.l_event_url leu
                                ON leu.entity0 = e.id
                              JOIN musicbrainz.url u
                                ON leu.entity1 = u.id
                              JOIN musicbrainz.link l
                                ON leu.link = l.id
                              JOIN musicbrainz.link_type lt
                                ON l.link_type = lt.id
                              {values_join}
                             WHERE lt.gid IN ({EVENT_URL_LINK_GIDS_SQL})
                               AND NOT l.ended
                          GROUP BY e.gid
                   ), event_tags AS (
                            SELECT e.gid AS event_mbid
                                 , array_agg(jsonb_build_array(t.name, et.count, g.gid)) AS event_tags
                              FROM musicbrainz.event e
                              JOIN musicbrainz.event_tag et
                                ON et.event = e.id
                              JOIN musicbrainz.tag t
                                ON et.tag = t.id
                         LEFT JOIN musicbrainz.genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE et.count > 0
                          GROUP BY e.gid
                   ), event_place AS (
                            SELECT DISTINCT ON (e.id)
                                   e.gid AS event_mbid
                                 , p.gid AS place_gid
                                 , p.name AS place_name
                                 , ar.gid AS area_gid
                                 , ar.name AS area_name
                              FROM musicbrainz.event e
                              JOIN musicbrainz.l_event_place lep
                                ON lep.entity0 = e.id
                              JOIN musicbrainz.link l
                                ON lep.link = l.id
                              JOIN musicbrainz.link_type lt
                                ON l.link_type = lt.id
                              JOIN musicbrainz.place p
                                ON lep.entity1 = p.id
                         LEFT JOIN musicbrainz.area ar
                                ON p.area = ar.id
                              {values_join}
                             WHERE lt.gid = '{EVENT_PLACE_LINK_GID}'
                          ORDER BY e.id, lep.id
                   ), event_area_fallback AS (
                            SELECT DISTINCT ON (e.id)
                                   e.gid AS event_mbid
                                 , ar.gid AS area_gid
                                 , ar.name AS area_name
                              FROM musicbrainz.event e
                              JOIN musicbrainz.l_area_event lae
                                ON lae.entity1 = e.id
                              JOIN musicbrainz.link l
                                ON lae.link = l.id
                              JOIN musicbrainz.link_type lt
                                ON l.link_type = lt.id
                              JOIN musicbrainz.area ar
                                ON lae.entity0 = ar.id
                         LEFT JOIN event_place ep
                                ON ep.event_mbid = e.gid
                              {values_join}
                             WHERE lt.gid = '{AREA_EVENT_LINK_GID}'
                               AND ep.event_mbid IS NULL
                          ORDER BY e.id, lae.id
                   ), event_art AS (
                            SELECT DISTINCT ON (ea.event)
                                   ea.event AS event_id
                                 , ea.id AS event_art_id
                              FROM event_art_archive.event_art ea
                              JOIN event_art_archive.event_art_type eat
                                ON eat.id = ea.id
                             WHERE eat.type_id = 1
                               AND ea.mime_type != 'application/pdf'
                          ORDER BY ea.event, ea.ordering
                   ), artist_edges AS (
                            SELECT e.gid AS event_mbid
                                 , array_agg(
                                        jsonb_build_array(
                                            a.gid
                                          , a.id
                                          , l.id
                                          , lt.gid
                                          , lt.name
                                          , lae.entity0_credit
                                        )
                                   ) AS edges
                              FROM musicbrainz.event e
                              JOIN musicbrainz.l_artist_event lae
                                ON lae.entity1 = e.id
                              JOIN musicbrainz.link l
                                ON lae.link = l.id
                              JOIN musicbrainz.link_type lt
                                ON l.link_type = lt.id
                              JOIN musicbrainz.artist a
                                ON lae.entity0 = a.id
                              {values_join}
                             WHERE lt.gid IN ({ARTIST_EVENT_LINK_GIDS_SQL})
                          GROUP BY e.gid
                   )
                            SELECT e.gid::TEXT AS event_mbid
                                 , e.id AS event_id
                                 , e.name AS event_name
                                 , e.begin_date_year
                                 , e.begin_date_month
                                 , e.begin_date_day
                                 , e.end_date_year
                                 , e.end_date_month
                                 , e.end_date_day
                                 , e.time AS event_time_raw
                                 , e.cancelled
                                 , e.ended
                                 , et.gid AS event_type_gid
                                 , et.name AS event_type_name
                                 , COALESCE(em.event_art_presence::TEXT, 'absent') AS event_art_presence
                                 , ep.place_gid AS place_mbid
                                 , ep.place_name AS place_name
                                 , COALESCE(ep.area_gid, eaf.area_gid) AS area_mbid
                                 , COALESCE(ep.area_name, eaf.area_name) AS area_name
                                 , e.comment AS disambiguation
                                 , e.setlist
                                 , eurl.event_links
                                 , etags.event_tags
                                 , ea.event_art_id
                                 , em.rating
                                 , em.rating_count
                                 , ae.edges AS artist_edges
                              FROM musicbrainz.event e
                         LEFT JOIN musicbrainz.event_type et
                                ON e.type = et.id
                         LEFT JOIN musicbrainz.event_meta em
                                ON em.id = e.id
                         LEFT JOIN event_url_rels eurl
                                ON eurl.event_mbid = e.gid
                         LEFT JOIN event_tags etags
                                ON etags.event_mbid = e.gid
                         LEFT JOIN event_place ep
                                ON ep.event_mbid = e.gid
                         LEFT JOIN event_area_fallback eaf
                                ON eaf.event_mbid = e.gid
                         LEFT JOIN event_art ea
                                ON ea.event_id = e.id
                         LEFT JOIN artist_edges ae
                                ON ae.event_mbid = e.gid
                              {values_join}
        """
        return query

    def query_last_updated_items(self, timestamp):
        # 1. Event core data: event itself, type, meta
        # |  CTE / table       |  purpose                    | last_updated considered
        # |  event             |  name, dates, cancelled     | event.last_updated
        event_mbids_query = """
            SELECT e.gid
              FROM musicbrainz.event e
             WHERE e.last_updated > %(timestamp)s
        """

        # 2. Event tags
        # |  CTE / table       |  purpose                    | last_updated considered
        # |  event_tags        |  community tags             | event_tag.last_updated, genre.last_updated
        event_tags_query = """
            SELECT e.gid
              FROM musicbrainz.event e
              JOIN musicbrainz.event_tag et
                ON et.event = e.id
              JOIN musicbrainz.tag t
                ON et.tag = t.id
         LEFT JOIN musicbrainz.genre g
                ON t.name = g.name
             WHERE et.last_updated > %(timestamp)s
                OR g.last_updated > %(timestamp)s
        """

        # Event URL rels
        # |  CTE / table       |  purpose                    | last_updated considered
        # |  event_url_rels    |  external links             | l_event_url, url, link_type
        event_url_rels_query = f"""
            SELECT e.gid
              FROM musicbrainz.event e
              JOIN musicbrainz.l_event_url leu
                ON leu.entity0 = e.id
              JOIN musicbrainz.url u
                ON leu.entity1 = u.id
              JOIN musicbrainz.link l
                ON leu.link = l.id
              JOIN musicbrainz.link_type lt
                ON l.link_type = lt.id
             WHERE lt.gid IN ({EVENT_URL_LINK_GIDS_SQL})
               AND (
                    leu.last_updated > %(timestamp)s
                 OR   u.last_updated > %(timestamp)s
                 OR  lt.last_updated > %(timestamp)s
               )
        """

        # Artist-event links
        # |  CTE / table       |  purpose                    | last_updated considered
        # |  artist_edges      |  performer relationships    | l_artist_event, link_type
        artist_event_query = f"""
            SELECT e.gid
              FROM musicbrainz.event e
              JOIN musicbrainz.l_artist_event lae
                ON lae.entity1 = e.id
              JOIN musicbrainz.link l
                ON lae.link = l.id
              JOIN musicbrainz.link_type lt
                ON l.link_type = lt.id
             WHERE lt.gid IN ({ARTIST_EVENT_LINK_GIDS_SQL})
               AND (
                    lae.last_updated > %(timestamp)s
                 OR  lt.last_updated > %(timestamp)s
               )
        """

        # Place and area data
        # |  CTE / table       |  purpose                    | last_updated considered
        # |  event_place       |  venue + area               | l_event_place, place, area
        place_query = f"""
            SELECT e.gid
              FROM musicbrainz.event e
              JOIN musicbrainz.l_event_place lep
                ON lep.entity0 = e.id
              JOIN musicbrainz.link l
                ON lep.link = l.id
              JOIN musicbrainz.link_type lt
                ON l.link_type = lt.id
              JOIN musicbrainz.place p
                ON lep.entity1 = p.id
         LEFT JOIN musicbrainz.area ar
                ON p.area = ar.id
             WHERE lt.gid = '{EVENT_PLACE_LINK_GID}'
               AND (
                    lep.last_updated > %(timestamp)s
                 OR   p.last_updated > %(timestamp)s
                 OR  ar.last_updated > %(timestamp)s
               )
        """

        # Area fallback
        area_query = f"""
            SELECT e.gid
              FROM musicbrainz.event e
              JOIN musicbrainz.l_area_event lae
                ON lae.entity1 = e.id
              JOIN musicbrainz.link l
                ON lae.link = l.id
              JOIN musicbrainz.link_type lt
                ON l.link_type = lt.id
              JOIN musicbrainz.area ar
                ON lae.entity0 = ar.id
             WHERE lt.gid = '{AREA_EVENT_LINK_GID}'
               AND (
                    lae.last_updated > %(timestamp)s
                 OR  ar.last_updated > %(timestamp)s
               )
        """

        try:
            with self.select_conn.cursor() as curs:
                self.config_postgres_join_limit(curs)
                event_mbids = set()

                log("mb event metadata cache: querying event core changes")
                curs.execute(event_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    event_mbids.add(row[0])

                log("mb event metadata cache: querying event tag changes")
                curs.execute(event_tags_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    event_mbids.add(row[0])

                log("mb event metadata cache: querying event url rel changes")
                curs.execute(event_url_rels_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    event_mbids.add(row[0])

                log("mb event metadata cache: querying artist-event link changes")
                curs.execute(artist_event_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    event_mbids.add(row[0])

                log("mb event metadata cache: querying place changes")
                curs.execute(place_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    event_mbids.add(row[0])

                log("mb event metadata cache: querying area fallback changes")
                curs.execute(area_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    event_mbids.add(row[0])

                return event_mbids
        except psycopg2.errors.OperationalError as err:
            log("mb event metadata cache: cannot query rows for update", err)
            return None

    def delete_rows(self, event_mbids: List[uuid.UUID]):
        """Delete event MBIDs from both cache tables."""

        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        with conn.cursor() as curs:
            curs.execute(
                f"DELETE FROM {self.table_name} WHERE event_mbid IN %s",
                (tuple(event_mbids),),
            )
            curs.execute(
                f"DELETE FROM {self.artist_cache.table_name} WHERE event_mbid IN %s",
                (tuple(event_mbids),),
            )

    def get_delete_rows_query(self):
        return f"DELETE FROM {self.table_name} WHERE event_mbid IN %s"

    def update_dirty_cache_items(self, event_mbids: Set[uuid.UUID]):
        if not event_mbids:
            log(f"{self.table_name} update: no dirty items found skipping update")
            return

        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            with self.select_conn.cursor(
                cursor_factory=psycopg2.extras.DictCursor
            ) as mb_curs:
                self.pre_insert_queries_db_setup(mb_curs)

                log(f"{self.table_name} update: Running query on dirty items")
                query = self.get_metadata_cache_query(with_values=True)
                values = [(mbid,) for mbid in event_mbids]
                psycopg2.extras.execute_values(
                    mb_curs, query, values, page_size=len(values)
                )

                rows = []
                artist_rows = []
                count = 0
                total_rows = len(event_mbids)
                for row in mb_curs:
                    count += 1
                    data = self.create_json_data(row)
                    rows.append(("false", self.last_updated, *data))
                    artist_rows.extend(self._create_artist_edge_rows(row))

                    if len(rows) >= self.batch_size:
                        batch_event_mbids = [row[2] for row in rows]
                        self.delete_rows(batch_event_mbids)
                        insert_rows(lb_curs, self.table_name, rows)
                        if artist_rows:
                            insert_rows(
                                lb_curs,
                                self.artist_cache.table_name,
                                artist_rows,
                                cols=self.artist_cache.insert_columns,
                            )
                        conn.commit()
                        log(
                            f"{self.table_name} update: inserted {count} rows. "
                            f"{100.0 * count / total_rows:.1f}%"
                        )
                        rows = []
                        artist_rows = []

                if rows:
                    batch_event_mbids = [row[2] for row in rows]
                    self.delete_rows(batch_event_mbids)
                    insert_rows(lb_curs, self.table_name, rows)
                    if artist_rows:
                        insert_rows(
                            lb_curs,
                            self.artist_cache.table_name,
                            artist_rows,
                            cols=self.artist_cache.insert_columns,
                        )
                    conn.commit()

        log(
            f"{self.table_name} update: inserted {count} rows. {100.0 * count / total_rows:.1f}%"
        )
        log(f"{self.table_name} update: Done!")


def create_mb_event_metadata_cache(use_lb_conn: bool):
    """
        Main function for creating the MB event metadata cache and its related tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """
    create_metadata_cache(
        MusicBrainzEventMetadataCache,
        MB_EVENT_METADATA_CACHE_TIMESTAMP_KEY,
        [],
        use_lb_conn,
    )


def incremental_update_mb_event_metadata_cache(use_lb_conn: bool):
    """Update the MB event metadata cache incrementally"""
    incremental_update_metadata_cache(
        MusicBrainzEventMetadataCache,
        MB_EVENT_METADATA_CACHE_TIMESTAMP_KEY,
        use_lb_conn,
    )
