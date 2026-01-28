from typing import Iterable
from uuid import UUID

from psycopg2.extras import execute_values


def get_caa_ids_for_release_mbids(curs, release_mbids: Iterable[str]):
    """ Given a list of release mbids, find the associated cover art for the releases. If cover art
     is missing for the release, fallback to the release group cover art if present.

     Returns a dictionary keyed by provided releases mbids, each key further maps to a dict having 3
     keys original_mbid (mbid of the provided release), caa_id and caa_release_mbid.

     Example:

        {
            "be5f714d-02eb-4c89-9a06-5e544f132604": {
                "original_mbid": "be5f714d-02eb-4c89-9a06-5e544f132604",
                "caa_id": 2273480607,
                "caa_release_mbid": "be5f714d-02eb-4c89-9a06-5e544f132604"
            },
            "4211382c-39e8-4a72-a32d-e4046fd96356": {
                "original_mbid": "4211382c-39e8-4a72-a32d-e4046fd96356",
                "caa_id": null,
                "caa_release_mbid": null
            },
            "773e54bb-3f43-4813-826c-ca762bfa8318": {
                "original_mbid": "773e54bb-3f43-4813-826c-ca762bfa8318",
                "caa_id": 9660646535,
                "caa_release_mbid": "3eee4ed1-b48e-4894-8a05-f535f16a4985"
            }
        }

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
                   , rel.name AS title
                   , ac.name AS artist
                FROM release_mbids rm
           LEFT JOIN musicbrainz.release rel
                  ON rel.gid = rm.mbid
           LEFT JOIN musicbrainz.artist_credit ac
                  ON ac.id = rel.artist_credit
           LEFT JOIN release_cover_art rca
                  ON rm.mbid = rca.original_mbid
           LEFT JOIN release_group_cover_art rgca
                  ON rm.mbid = rgca.original_mbid
    """
    result = execute_values(curs, query, [(UUID(mbid),) for mbid in release_mbids], fetch=True)
    return {row["original_mbid"]: row for row in result}


def get_caa_ids_for_release_group_mbids(curs, release_group_mbids: Iterable[str]):
    """Given a list of release group mbids, find the associated cover art for the release groups.

       Returns a dictionary similar to `get_caa_ids_for_release_mbids()`
    """
    query = """
          WITH release_group_mbids(mbid) AS (
                    VALUES %s
            ) SELECT DISTINCT ON(rg.id)
                           rgm.mbid::TEXT AS original_mbid
                         , caa.id AS caa_id
                         , caa_rel.gid::TEXT AS caa_release_mbid
                         , rg.name as title
                         , rg.artist_credit as artist
                      FROM release_group_mbids rgm
                      JOIN musicbrainz.release_group rg
                        ON rg.id = rgm.mbid::uuid
                      JOIN musicbrainz.release caa_rel
                        ON rg.id = caa_rel.release_group
                 FULL JOIN cover_art_archive.release_group_cover_art rgca
                        ON rgca.release = caa_rel.id
                 LEFT JOIN cover_art_archive.cover_art caa
                        ON caa.release = caa_rel.id
                 LEFT JOIN cover_art_archive.cover_art_type cat
                        ON cat.id = caa.id
                     WHERE type_id = 1
                       AND mime_type != 'application/pdf'
    """
    result = execute_values(curs, query, [(UUID(mbid),) for mbid in release_group_mbids], fetch=True)
    return {row["original_mbid"]: row for row in result}
