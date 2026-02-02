from uuid import UUID

import psycopg2
import psycopg2.extras
from datasethoster import Query
from flask import current_app
from pydantic import BaseModel


class ArtistCreditIdFromArtistMBIDInput(BaseModel):
    artist_mbid: UUID


class ArtistCreditIdFromArtistMBIDOutput(BaseModel):
    artist_mbid: UUID
    artist_credit_id: list[int]


class ArtistCreditIdFromArtistMBIDQuery(Query):

    def names(self):
        return "artist-credit-from-artist-mbid", "MusicBrainz Artist Credit From Artist MBID"

    def inputs(self):
        return ArtistCreditIdFromArtistMBIDInput

    def introduction(self):
        return """Look up all available artist credit ids from an artist mbid."""

    def outputs(self):
        return ArtistCreditIdFromArtistMBIDOutput

    def fetch(self, params, source, count=-1, offset=-1):
        if not current_app.config["MB_DATABASE_URI"]:
            return []

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

                acs = tuple([p.artist_mbid for p in params])
                query = """SELECT a.gid AS artist_mbid,
                                       array_agg(ac.id) AS artist_credit_id
                                  FROM artist_credit ac
                                  JOIN artist_credit_name acn
                                    ON ac.id = acn.artist_credit
                                  JOIN artist a
                                    ON acn.artist = a.id
                                 WHERE a.gid in %s
                              GROUP BY a.gid
                              ORDER BY artist_mbid"""
                args = [acs]
                if count > 0:
                    query += " LIMIT %s"
                    args.append(count)
                if offset >= 0:
                    query += " OFFSET %s"
                    args.append(offset)

                curs.execute(query, tuple(args))
                output = []
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    output.append(dict(row))

                return [ArtistCreditIdFromArtistMBIDOutput(**row) for row in output]
