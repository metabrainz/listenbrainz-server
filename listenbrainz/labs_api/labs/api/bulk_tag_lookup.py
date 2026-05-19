from uuid import UUID

from flask import current_app
from pydantic import BaseModel
from werkzeug.exceptions import BadRequest
import psycopg2
import psycopg2.extras

from datasethoster import Query


class BulkTagLookupInput(BaseModel):
    recording_mbid: str


class BulkTagLookupOutput(BaseModel):
    recording_mbid: UUID
    tag: str
    tag_count: int
    percent: float
    source: str


class BulkTagLookup(Query):
    '''
        Look up a tag and popularity data for a list of recordings, based on MBID.
    '''

    def names(self):
        return "bulk-tag-lookup", "Bulk MusicBrainz Tag/Popularity by recording MBID Lookup"

    def inputs(self):
        return BulkTagLookupInput

    def introduction(self):
        return """Look up tag and popularity information given a recording MBID"""

    def outputs(self):
        return BulkTagLookupOutput

    def fetch(self, params, source, offset=-1, count=-1):

        mbids = []
        for p in params:
            for mbid in p.recording_mbid.split(","):
                mbid = mbid.strip()
                if mbid:
                    mbids.append(mbid)

        if len(mbids) > 1000:
            raise BadRequest("Cannot lookup more than 1,000 recordings at a time.")

        if not mbids:
            return []

        with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_PGBOUNCER_URI"]) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                query = '''SELECT recording_mbid
                                , tag
                                , tag_count
                                , percent
                                , source
                             FROM tags.lb_tag_radio
                            WHERE recording_mbid IN %s'''

                curs.execute(query, (tuple(mbids),))
                output = []
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    output.append(BulkTagLookupOutput(**row))

        return output
