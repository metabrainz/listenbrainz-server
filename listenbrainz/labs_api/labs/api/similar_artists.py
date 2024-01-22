import psycopg2
from datasethoster import Query
from flask import current_app
from markupsafe import Markup
from psycopg2.extras import execute_values

from listenbrainz.db import similarity
from listenbrainz.db.artist import load_artists_from_mbids_with_redirects


class SimilarArtistsViewerQuery(Query):
    """ Display similar artists calculated using a given algorithm """

    def setup(self):
        pass

    def names(self):
        return "similar-artists", "Similar Artists Viewer"

    def inputs(self):
        return ['artist_mbid', 'algorithm']

    def introduction(self):
        return """This page allows you to view artists similar to a given artist and algorithm."""

    def outputs(self):
        return None

    def fetch(self, params, offset=-1, count=-1):
        artist_mbids = params[0]["artist_mbid"].strip().split(",")
        algorithm = params[0]["algorithm"].strip()
        count = count if count > 0 else 100

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:

            references = load_artists_from_mbids_with_redirects(mb_curs, artist_mbids)
            results = [
                {
                    "type": "markup",
                    "data": Markup("<p><b>Reference artist</b></p>")
                },
                {
                    "type": "dataset",
                    "columns": list(references[0].keys()),
                    "data": references
                }
            ]

            similar_artists = similarity.get_artists(mb_curs, ts_curs, artist_mbids, algorithm, count)
            if len(similar_artists) == 0:
                results.append({
                    "type": "markup",
                    "data": Markup("<p><b>No similar artists found!</b></p>")
                })
                return results

            results.append({
                "type": "markup",
                "data": Markup("<p><b>Similar artists</b></p>")
            })
            results.append({
                "type": "dataset",
                "columns": list(similar_artists[0].keys()),
                "data": similar_artists
            })

            return results
