#!/usr/bin/env python3

import psycopg2
import psycopg2.extras
from datasethoster import Query
from datasethoster.main import register_query
from flask import current_app


class ArtistCreditIdFromArtistMSIDQuery(Query):

    def names(self):
        return ("artist-credit-from-artist-msid", "MusicBrainz Artist Credit From Artist MSID")

    def inputs(self):
        return ['artist_msid']

    def introduction(self):
        return """This page allows you to lookup an artist_msid and get a list of possible
                  artist_credit_ids."""

    def outputs(self):
        return ['artist_msid', 'artist_credit_id', '[artist_credit_mbid]', 'artist_credit_name']

    def fetch(self, params, offset=-1, count=-1):

        msid = tuple([p['artist_msid'] for p in params])
        with psycopg2.connect(current_app.config['DB_CONNECT_MAPPING']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                query = """SELECT map.artist_msid as artist_msid,
                                       ac.id AS artist_credit_id,
                                       ac.name AS artist_credit_name,
                                       array_agg(a.gid) AS artist_credit_mbid
                                  FROM artist_credit ac
                                  JOIN artist_credit_name acn
                                    ON ac.id = acn.artist_credit
                                  JOIN artist a
                                    ON acn.artist = a.id
                                  JOIN (SELECT DISTINCT mb_artist_credit_id AS artist_credit_id,
                                                        msb_artist_msid AS artist_msid
                                                   FROM mapping.msid_mbid_mapping m
                                                  WHERE msb_artist_msid in %s) AS map(artist_credit_id, artist_msid)
                                    ON ac.id = map.artist_credit_id
                              GROUP BY map.artist_msid, ac.id, ac.name
                              ORDER BY artist_credit_id"""
                args = [msid]
                if count > 0:
                    query += " LIMIT %s"
                    args.append(count)
                if offset >= 0:
                    query += " OFFSET %s"
                    args.append(offset)

                curs.execute(query, tuple(args))
                results = []
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    r = dict(row)
                    r['artist_msid'] = str(r['artist_msid'])
                    r['[artist_credit_mbid]'] = [str(u) for u in r['artist_credit_mbid'][1:-1].split(',')]
                    del r['artist_credit_mbid']
                    results.append(r)

                return results
