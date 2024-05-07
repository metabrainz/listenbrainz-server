from uuid import UUID

from datasethoster import Query
import psycopg2
import psycopg2.extras
from flask import current_app
from pydantic import BaseModel


class ArtistCountryFromArtistMBIDInput(BaseModel):
    artist_mbid: UUID


class ArtistCountryFromArtistMBIDOutput(BaseModel):
    artist_mbid: UUID
    artist_name: str
    country_code: str
    area_id: int


class ArtistCountryFromArtistMBIDQuery(Query):

    def names(self):
        return "artist-country-code-from-artist-mbid", "MusicBrainz Artist Country From Artist MBID"

    def inputs(self):
        return ArtistCountryFromArtistMBIDInput

    def introduction(self):
        return """Given artist MBIDs look up countries for those artists. Any artist_mbids
                  not found in the database will be omitted from the results. If none are
                  found a 404 error is returned."""

    def outputs(self):
        return ArtistCountryFromArtistMBIDOutput

    def fetch(self, params: list[ArtistCountryFromArtistMBIDInput], source, count=-1, offset=-1) -> list[ArtistCountryFromArtistMBIDOutput]:
        if not current_app.config["MB_DATABASE_URI"]:
            return []

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

                acs = tuple([r.artist_mbid for r in params])
                query = """ SELECT a.gid AS artist_mbid,
                                   a.name AS artist_name,
                                   ar.id AS area_id,
                                   code AS country_code
                              FROM artist a
                              JOIN area ar
                                ON a.area = ar.id
                  FULL OUTER JOIN iso_3166_1 iso
                                ON iso.area = ar.id
                             WHERE a.gid IN %s
                          ORDER BY artist_mbid"""

                args = [acs]
                if count > 0:
                    query += " LIMIT %s"
                    args.append(count)
                if offset >= 0:
                    query += " OFFSET %s"
                    args.append(offset)

                curs.execute(query, tuple(args))
                areas = []
                mapping = []
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    r = dict(row)
                    areas.append(r['area_id'])
                    mapping.append(r)

                if not areas:
                    return []

                areas = tuple(areas)
                curs.execute("""WITH RECURSIVE area_descendants AS (
                                        SELECT entity0 AS parent, entity1 AS descendant, 1 AS depth
                                          FROM l_area_area laa
                                          JOIN link ON laa.link = link.id
                                         WHERE link.link_type = 356
                                           AND entity1 IN %s
                                         UNION
                                        SELECT entity0 AS parent, descendant, (depth + 1) AS depth
                                          FROM l_area_area laa
                                          JOIN link ON laa.link = link.id
                                          JOIN area_descendants ON area_descendants.parent = laa.entity1
                                         WHERE link.link_type = 356
                                           AND entity0 != descendant
                                        )
                                        SELECT descendant AS area, iso.code AS country_code
                                          FROM area_descendants ad
                                          JOIN iso_3166_1 iso ON iso.area = ad.parent""", (areas,))
                area_index = {}
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    r = dict(row)
                    area_index[r['area']] = r['country_code']

                for i, row in enumerate(mapping):
                    if not row['country_code']:
                        try:
                            mapping[i]['country_code'] = area_index[row['area_id']]
                        except KeyError:
                            mapping[i]['country_code'] = ''

                return [ArtistCountryFromArtistMBIDOutput(**row) for row in mapping]
