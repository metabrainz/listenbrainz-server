from typing import Iterable
from uuid import UUID

from psycopg2.extras import execute_values


def get_caa_ids_for_release_mbids(curs, release_mbids: Iterable[str]):
    """ Given a list of release mbids, find the associated cover art for the releases. If cover art
     is missing for the release, fallback to the release group cover art if present.
    """
    query = """
          WITH release_mbids(mbid) AS (
                    VALUES %s
            ), release_cover_art AS (
                    SELECT DISTINCT ON (rm.mbid)
                           rm.mbid AS original_mbid
                         , caa.id AS caa_id
                         , rm.mbid AS caa_release_mbid
                      FROM release_mbids rm
                      JOIN musicbrainz.release rel
                        ON rel.gid = rm.mbid
                      JOIN cover_art_archive.cover_art caa
                        ON caa.release = rel.id
                      JOIN cover_art_archive.cover_art_type cat
                        ON cat.id = caa.id
                     WHERE type_id = 1
                       AND mime_type != 'application/pdf'
                  ORDER BY rm.mbid
                         , caa.ordering
            ), release_group_cover_art AS (
                    SELECT DISTINCT ON(rg.id)
                           mbid AS original_mbid
                         , caa.id AS caa_id
                         , caa_rel.gid AS caa_release_mbid
                      FROM release_mbids rm
                      JOIN musicbrainz.release rel
                        ON rel.gid = rm.mbid::uuid
                      JOIN musicbrainz.release_group rg
                        ON rg.id = rel.release_group
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
                     WHERE type_id = 1
                       AND mime_type != 'application/pdf'
                  ORDER BY rg.id
                         , rgca.release
                         , re.date_year
                         , re.date_month
                         , re.date_day
                         , caa.ordering
            ) SELECT rm.mbid::TEXT AS original_mbid
                   , COALESCE(rca.caa_id, rgca.caa_id) AS caa_id
                   , COALESCE(rca.caa_release_mbid, rgca.caa_release_mbid)::TEXT AS caa_release_mbid
                FROM release_mbids rm
           LEFT JOIN release_cover_art rca
                  ON rm.mbid = rca.original_mbid
           LEFT JOIN release_group_cover_art rgca
                  ON rm.mbid = rgca.original_mbid
    """
    result = execute_values(curs, query, [(UUID(mbid),) for mbid in release_mbids], fetch=True)
    return {row["original_mbid"]: row for row in result}
