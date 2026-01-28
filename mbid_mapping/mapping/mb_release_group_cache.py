import uuid

import uuid

import psycopg2
import psycopg2.extras
import ujson

import config
from mapping.mb_cache_base import create_metadata_cache, MusicBrainzEntityMetadataCache, \
    incremental_update_metadata_cache, ARTIST_LINK_GIDS_SQL
from mapping.utils import log

MB_RELEASE_GROUP_CACHE_TIMESTAMP_KEY = "mb_release_group_cache_last_update_timestamp"


RELEASE_GROUP_LINK_GIDS = (
    '5e2907db-49ec-4a48-9f11-dfb99d2603ff',
    'b41e7530-cde4-459c-b8c5-dfef08fc8295',
    'cee8e577-6fa6-4d77-abc0-35bce13c570e',
)
RELEASE_GROUP_LINK_GIDS_SQL = ", ".join([f"'{x}'" for x in RELEASE_GROUP_LINK_GIDS])


class MusicBrainzReleaseGroupCache(MusicBrainzEntityMetadataCache):
    """
        This class creates the MB release group cache

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__("mapping.mb_release_group_cache", select_conn, insert_conn, batch_size, unlogged)

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


        date = ''
        if row["year"] is not None:
            date = str(row["year"])
            if row["month"] is not None:
                date += "-%02d" % row["month"]
                if row["day"] is not None:
                    date += "-%02d" % row["day"]

        release_group = {
            "name": row["release_group_name"],
            "date": date,
            "type": row["type"],
            "caa_id": row["caa_id"],
            "caa_release_mbid": row["caa_release_mbid"],
            "rels": release_group_rels
        }

        all_recordings = []
        mediums = []
        for medium_name, medium_position, medium_format, tracks in row["mediums"] or []:
            recordings = []
            for position, name, recording_mbid, length, ac_parts in tracks or []:
                recording_artist_mbids = []
                recording_artists = []

                for artist_mbid, ac_name, ac_jp in ac_parts:
                    recording_artist_mbids.append(artist_mbid)
                    recording_artists.append({
                        "artist_mbid": artist_mbid,
                        "artist_credit_name": ac_name,
                        "join_phrase": ac_jp
                    })

                recordings.append({
                    "recording_mbid": recording_mbid,
                    "name": name,
                    "position": position,
                    "length": length,
                    "artists": recording_artists,
                    "artist_mbids": recording_artist_mbids
                })

            mediums.append({
                "name": medium_name,
                "position": medium_position,
                "format": medium_format,
                "tracks": recordings
            })
            all_recordings.extend(recordings)

        return (row["release_group_mbid"],
                artist_mbids,
                ujson.dumps(artist),
                ujson.dumps({"artist": artist_tags, "release_group": release_group_tags}),
                ujson.dumps(release_group),
                ujson.dumps({
                    "release_mbid": str(row["recordings_release_mbid"]),
                    "recordings": all_recordings,
                    "mediums": mediums
                }))

    def get_metadata_cache_query(self, with_values=False):
        values_cte = ""
        values_join = ""
        if with_values:
            values_cte = "subset (subset_release_group_mbid) AS (values %s), "
            values_join = "JOIN subset ON rg.gid = subset.subset_release_group_mbid"

        query = f"""WITH {values_cte} artist_rels AS (
                                SELECT a.gid
                                     , array_agg(distinct(ARRAY[lt.name, url])) AS artist_links
                                  FROM musicbrainz.release_group rg
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
                                 -- do not show outdated urls to users
                                   AND NOT l.ended
                              GROUP BY a.gid
                   ), release_group_rels AS (
                                SELECT rg.gid
                                     , array_agg(ARRAY[lt.name, a1.name, a1.gid::TEXT, lat.name]) AS release_group_links
                                  FROM musicbrainz.release_group rg
                                  JOIN musicbrainz.l_artist_release_group lar
                                    ON lar.entity1 = rg.id
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
                                 -- the release group rels we use make sense to be shown to the user even if they have been marked as ended
                               GROUP BY rg.gid
                   ), artist_data AS (
                            SELECT rg.gid
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
                              FROM musicbrainz.release_group rg
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
                          GROUP BY rg.gid
                   ), artist_tags AS (
                            SELECT rg.gid AS release_group_mbid
                                 , array_agg(jsonb_build_array(t.name, count, a.gid, g.gid)) AS artist_tags
                              FROM musicbrainz.release_group rg
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
                          GROUP BY rg.gid
                   ), release_group_tags AS (
                            SELECT rg.gid AS release_group_mbid
                                 , array_agg(jsonb_build_array(t.name, count, g.gid)) AS release_group_tags
                              FROM musicbrainz.release_group rg
                              JOIN musicbrainz.release_group_tag rgt
                                ON rg.id = rgt.release_group
                              JOIN musicbrainz.tag t
                                ON rgt.tag = t.id
                         LEFT JOIN musicbrainz.genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                          GROUP BY rg.gid
                   ), rg_cover_art AS (
                            SELECT DISTINCT ON(rg.id)
                                   rg.id AS release_group
                                 , caa_rel.gid::TEXT AS caa_release_mbid
                                 , caa.id AS caa_id
                              FROM musicbrainz.release_group rg
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
                   ), recording_artist_data AS (
                           SELECT release_group_mbid
                                , rel.gid AS recordings_release_mbid
                                , m.name AS medium_name
                                , m.position AS medium_position
                                , mf.name AS medium_format
                                , t.position AS track_position
                                , r.name AS recording_name
                                , r.gid::TEXT AS recording_mbid
                                , r.length AS recording_length
                                , jsonb_agg(
                                    jsonb_build_array(
                                        a.gid::TEXT
                                      , acn.name
                                      , acn.join_phrase
                                    )
                                    ORDER BY acn.position
                                   ) AS artists
                             FROM canonical_release_selection crs
                             JOIN musicbrainz.release rel
                               ON rel.id = crs.release_id
                             JOIN musicbrainz.medium m
                               ON m.release = rel.id
                        LEFT JOIN musicbrainz.medium_format mf
                               ON mf.id = m.format
                             JOIN musicbrainz.track t
                               ON t.medium = m.id
                             JOIN musicbrainz.recording r
                               ON r.id = t.recording
                             JOIN musicbrainz.artist_credit_name acn
                               ON r.artist_credit = acn.artist_credit
                             JOIN musicbrainz.artist a
                               ON acn.artist = a.id
                         GROUP BY release_group_mbid
                                , rel.gid
                                , medium_name
                                , medium_position
                                , medium_format
                                , track_position
                                , recording_name
                                , recording_mbid
                                , recording_length
                   ), recording_medium_data AS (
                           SELECT release_group_mbid
                                , recordings_release_mbid
                                , medium_name
                                , medium_position
                                , medium_format
                                , array_agg(
                                        jsonb_build_array(
                                            track_position
                                          , recording_name
                                          , recording_mbid
                                          , recording_length
                                          , artists
                                        ) ORDER BY track_position
                                  ) AS tracks
                             FROM recording_artist_data rad
                         GROUP BY release_group_mbid
                                , recordings_release_mbid
                                , medium_name
                                , medium_position
                                , medium_format
                   ), recording_data AS (
                           SELECT release_group_mbid
                                , recordings_release_mbid
                                , array_agg(
                                        jsonb_build_array(
                                            medium_name
                                          , medium_position
                                          , medium_format
                                          , tracks
                                        ) ORDER BY medium_position
                                  ) AS mediums
                             FROM recording_medium_data
                         GROUP BY release_group_mbid
                                , recordings_release_mbid
                   )
                            SELECT release_group_links
                                 , rg.name AS release_group_name
                                 , rg.artist_credit AS artist_credit_id
                                 , ac.name AS artist_credit_name
                                 , artist_data
                                 , artist_tags
                                 , release_group_tags
                                 , rg.gid::TEXT AS release_group_mbid
                                 , rgca.caa_id
                                 , rgca.caa_release_mbid
                                 , rgpt.name AS type
                                 , rgm.first_release_date_year AS year
                                 , rgm.first_release_date_month AS month
                                 , rgm.first_release_date_day AS day
                                 , rec_data.mediums
                                 , rec_data.recordings_release_mbid
                              FROM musicbrainz.release_group rg
                              JOIN musicbrainz.artist_credit ac
                                ON rg.artist_credit = ac.id
                         LEFT JOIN musicbrainz.release_group_primary_type rgpt
                                ON rg.type = rgpt.id
                         LEFT JOIN musicbrainz.release_group_meta rgm
                                ON rgm.id = rg.id
                         LEFT JOIN artist_data ard
                                ON ard.gid = rg.gid
                         LEFT JOIN release_group_rels rrl
                                ON rrl.gid = rg.gid
                         LEFT JOIN release_group_tags rt
                                ON rt.release_group_mbid = rg.gid
                         LEFT JOIN artist_tags ats
                                ON ats.release_group_mbid = rg.gid
                         LEFT JOIN rg_cover_art rgca
                                ON rgca.release_group = rg.id
                         LEFT JOIN recording_data rec_data
                                ON rec_data.release_group_mbid = rg.gid
                              {values_join}
                          GROUP BY rg.gid
                                 , rg.name
                                 , rg.artist_credit
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
                                 , rec_data.mediums
                                 , rec_data.recordings_release_mbid
                   """
        return query

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
            ) SELECT rg.gid
                FROM musicbrainz.release_group rg
                JOIN musicbrainz.artist_credit_name acn
               USING (artist_credit)
                JOIN artist_mbids am
                  ON acn.artist = am.id
        """

        # 2. recording_rels, recording_tags, recording
        # these CTEs concern recording data and we fetch release_group_mbids from these. the CTEs do not join to artist
        # table because that has been considered earlier.
        #
        # |  CTE / table        |        purpose             | last_updated considered           | last_updated ignored
        # |  release_group_rels |  artist - recording links  | link relationship related and url | release_group, artist
        # |  release_group_tags |  release_group tags        | release_group_tag, genre          | release_group
        # |  release_group      |                            | release_group                     |
        release_group_mbids_query = f"""
                SELECT rg.gid
                  FROM musicbrainz.release_group rg
                  JOIN musicbrainz.l_artist_release_group lar
                    ON lar.entity1 = rg.id
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
                SELECT rg.gid
                  FROM musicbrainz.tag t
                  JOIN musicbrainz.release_group_tag rt
                    ON rt.tag = t.id
                  JOIN musicbrainz.release_group rg
                    ON rt.release_group = rg.id
             LEFT JOIN musicbrainz.genre g
                    ON t.name = g.name
                 WHERE rt.last_updated > %(timestamp)s
                    OR  g.last_updated > %(timestamp)s
            UNION
                SELECT rg.gid
                  FROM musicbrainz.release_group rg
                 WHERE rg.last_updated > %(timestamp)s
        """

        # 3. canonical_release_selection, recordings_data
        # these CTEs concern release data and we fetch release and cover art data from these.
        recordings_query = """
            WITH canonical_release_selection AS (
                    SELECT DISTINCT ON (rg.gid)
                           rg.gid AS release_group_mbid
                         , rel.id AS release_id
                      FROM musicbrainz.release_group rg
                      JOIN musicbrainz.release rel
                        ON rel.release_group = rg.id
                      JOIN mapping.canonical_release crl
                        ON rel.id = crl.release
                  ORDER BY rg.gid
                         , crl.id
            )
                   SELECT release_group_mbid
                     FROM musicbrainz.recording r
                     JOIN musicbrainz.track t
                       ON t.recording = r.id
                     JOIN musicbrainz.medium m
                       ON t.medium = m.id
                     JOIN musicbrainz.release rel
                       ON m.release = rel.id
                     JOIN canonical_release_selection crs
                       ON rel.id = crs.release_id
                    WHERE r.last_updated > %(timestamp)s
                       OR t.last_updated > %(timestamp)s
                       OR m.last_updated > %(timestamp)s
                 GROUP BY release_group_mbid
        """

        try:
            with self.select_conn.cursor() as curs:
                self.config_postgres_join_limit(curs)
                release_group_mbids = set()

                log("mb release group metadata cache: querying release group mbids to update")
                curs.execute(release_group_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    release_group_mbids.add(row[0])

                log("mb release group metadata cache: querying artist mbids to update")
                curs.execute(artist_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    release_group_mbids.add(row[0])

                log("mb release group metadata cache: querying recording mbids to update")
                curs.execute(recordings_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    release_group_mbids.add(row[0])

                return release_group_mbids
        except psycopg2.errors.OperationalError as err:
            log("mb release group metadata cache: cannot query rows for update", err)
            return None

    def get_delete_rows_query(self):
        return f"DELETE FROM {self.table_name} WHERE release_group_mbid IN %s"


def create_mb_release_group_cache(use_lb_conn: bool):
    """
        Main function for creating the MB release group cache and its related tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """
    create_metadata_cache(MusicBrainzReleaseGroupCache, MB_RELEASE_GROUP_CACHE_TIMESTAMP_KEY, [], use_lb_conn)


def incremental_update_mb_release_group_cache(use_lb_conn: bool):
    """ Update the MB metadata cache incrementally """
    incremental_update_metadata_cache(MusicBrainzReleaseGroupCache, MB_RELEASE_GROUP_CACHE_TIMESTAMP_KEY, use_lb_conn)
