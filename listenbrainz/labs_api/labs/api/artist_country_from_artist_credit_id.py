from operator import itemgetter

from datasethoster import Query
import psycopg2
import psycopg2.extras
from werkzeug.exceptions import NotFound
from listenbrainz import config


class ArtistCountryFromArtistCreditIdQuery(Query):

    def names(self):
        return ("artist-country-code-from-artist-credit-id", "MusicBrainz Artist Country From Artist Credit Id")

    def inputs(self):
        return ['[artist_credit_id]']

    def introduction(self):
        return """Given artist credit id look up countries for those artists. Any artist_mbids
                  not found in the database will be omitted from the results. If none are
                  found a 404 error is returned."""

    def outputs(self):
        return ['artist_credit_id', 'artist_mbid', 'country_code']

    def fetch(self, params, count=-1, offset=-1):

        with psycopg2.connect(config.MB_DATABASE_URI) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

                acs = tuple([r['[artist_credit_id]'] for r in params])
                query = """ SELECT a.gid AS artist_mbid,
                                    ar.id AS area_id,
                                    code AS country_code,
                                    ac.id AS artist_credit_id
                               FROM artist a
                               JOIN artist_credit_name acn
                                 ON acn.artist = a.id
                               JOIN artist_credit ac
                                 ON acn.artist_credit = ac.id
                               JOIN area ar
                                 ON a.area = ar.id
                    FULL OUTER JOIN iso_3166_1 iso
                                 ON iso.area = ar.id
                              WHERE ac.id IN %s
                           ORDER BY artist_credit_id"""

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
                    mapping.append(dict(row))

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


                result = []
                for i, row in enumerate(mapping):
                    if not row['country_code']:
                        try:
                            mapping[i]['country_code'] = area_index[row['area_id']]
                        except KeyError:
                            mapping[i]['country_code'] = ''

                return mapping
