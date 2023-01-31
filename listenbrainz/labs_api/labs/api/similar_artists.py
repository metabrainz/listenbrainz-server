import psycopg2
from datasethoster import Query
from flask import current_app
from markupsafe import Markup
from psycopg2.extras import execute_values

from listenbrainz.db import similarity
from listenbrainz.db.recording import resolve_redirect_mbids


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

    @staticmethod
    def get_artists_dataset(mb_curs, mbids, score_idx=None, similar_mbid_idx=None):
        """ Retrieve artist metadata for given list of mbids after resolving redirects and adding similarity
         data if available """
        redirected_mbids, index, inverse_index = resolve_redirect_mbids(mb_curs, "artist", mbids)
        query = """
                WITH mbids (gid) AS (VALUES %s)
              SELECT a.gid::TEXT AS artist_mbid
                   , a.name
                   , a.comment
                   , t.name AS type
                   , g.name AS gender
                FROM musicbrainz.artist a
           LEFT JOIN musicbrainz.artist_type t
                  ON t.id = a.type
           LEFT JOIN musicbrainz.gender g
                  ON g.id = a.gender
                JOIN mbids m
                  ON a.gid = m.gid::UUID
        """
        results = execute_values(mb_curs, query, [(mbid,) for mbid in redirected_mbids], fetch=True)
        metadata_idx = {row["artist_mbid"]: row for row in results}

        metadata = []
        for mbid in mbids:
            redirected_mbid = index.get(mbid, mbid)
            if redirected_mbid not in metadata_idx:
                item = {
                    "artist_mbid": mbid,
                    "name": None,
                    "comment": None,
                    "type": None,
                    "gender": None
                }
            else:
                data = metadata_idx[redirected_mbid]
                item = dict(data)

            if score_idx and similar_mbid_idx:
                item["score"] = score_idx.get(mbid)
                item["reference_mbid"] = similar_mbid_idx.get(mbid)

            metadata.append(item)

        return {
            "type": "dataset",
            "columns": list(metadata[0].keys()),
            "data": metadata
        }

    def fetch(self, params, offset=-1, count=-1):
        artist_mbids = params[0]["artist_mbid"].strip().split(",")
        algorithm = params[0]["algorithm"].strip()
        count = count if count > 0 else 100

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:

            references = self.get_artists_dataset(mb_curs, artist_mbids)
            results = [{"type": "markup", "data": Markup("<p><b>Reference artist</b></p>")}]
            results.append(references)

            similar_mbids, score_idx, mbid_idx = similarity.get(ts_curs, "artist_credit_mbids", artist_mbids, algorithm, count)
            if len(similar_mbids) == 0:
                results.append({
                    "type": "markup",
                    "data": Markup("<p><b>No similar artists found!</b></p>")
                })
                return results

            similar_dataset = self.get_artists_dataset(mb_curs, similar_mbids, score_idx, mbid_idx)
            results.append({"type": "markup", "data": Markup("<p><b>Similar artists</b></p>")})
            results.append(similar_dataset)

            return results
