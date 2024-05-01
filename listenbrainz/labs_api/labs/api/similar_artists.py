from typing import Optional, Union
from uuid import UUID

import psycopg2
from datasethoster import Query, RequestSource, QueryOutputLine
from flask import current_app
from markupsafe import Markup
from psycopg2.extras import execute_values
from pydantic import BaseModel

from listenbrainz.db import similarity
from listenbrainz.db.artist import load_artists_from_mbids_with_redirects


class SimilarArtistsViewerInput(BaseModel):
    artist_mbids: list[UUID]
    algorithm: str


class SimilarArtistsViewerOutputItem(BaseModel):
    artist_mbid: Optional[UUID]
    name: Optional[str]
    comment: Optional[str]
    type: Optional[str]
    gender: Optional[str]
    score: Optional[int]
    reference_mbid: Optional[str]


SimilarArtistsViewerOutput = Union[QueryOutputLine, SimilarArtistsViewerOutputItem]


class SimilarArtistsViewerQuery(Query):
    """ Display similar artists calculated using a given algorithm """

    def setup(self):
        pass

    def names(self):
        return "similar-artists", "Similar Artists Viewer"

    def inputs(self):
        return SimilarArtistsViewerInput

    def introduction(self):
        return """This page allows you to view artists similar to a given artist and algorithm."""

    def outputs(self):
        return SimilarArtistsViewerOutput

    def fetch(self, params, source, offset=-1, count=-1):
        artist_mbids = [str(m) for m in params[0].artist_mbids]
        algorithm = params[0].algorithm.strip()
        count = count if count > 0 else 100

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:
            results = []

            if source == RequestSource.web:
                references = load_artists_from_mbids_with_redirects(mb_curs, artist_mbids)
                results.append(QueryOutputLine(line=Markup("<p><b>Reference artists</b></p>")))
                results.extend([SimilarArtistsViewerOutputItem(**artist) for artist in references])

            similar_artists = similarity.get_artists(mb_curs, ts_curs, artist_mbids, algorithm, count)
            if source == RequestSource.web:
                if len(similar_artists) == 0:
                    results.append(QueryOutputLine(line=Markup("<p><b>No similar artists found!</b></p>")))
                    return results
                else:
                    results.append(QueryOutputLine(line=Markup("<p><b>Similar artists</b></p>")))

            results.extend([SimilarArtistsViewerOutputItem(**artist) for artist in similar_artists])

            return results
