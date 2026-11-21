from contextlib import closing
from uuid import UUID

from pydantic import BaseModel, validator
from werkzeug.exceptions import BadRequest
import psycopg2
import psycopg2.extras

from datasethoster import Query, RequestSource

from listenbrainz.db import listens as listens_db


class BulkTagLookupInput(BaseModel):
    recording_mbid: list[UUID]

    @validator("recording_mbid", pre=True)
    def parse_recording_mbids(cls, value):
        if isinstance(value, (str, UUID)):
            value = [value]
        if isinstance(value, list):
            return [
                mbid.strip()
                for entry in value
                for mbid in str(entry).split(",")
                if mbid.strip()
            ]
        return value


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

    def fetch(
        self,
        params: list[BulkTagLookupInput],
        source: RequestSource,
        offset: int = -1,
        count: int = -1,
    ) -> list[BulkTagLookupOutput]:

        mbids = tuple(mbid for param in params for mbid in param.recording_mbid)
        if len(mbids) > 1000:
            raise BadRequest("Cannot lookup more than 1,000 recordings at a time.")

        if not mbids:
            return []

        with (
            closing(listens_db.engine.raw_connection()) as conn,
            conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs
        ):
            query = '''SELECT recording_mbid
                            , tag
                            , tag_count
                            , percent
                            , source
                         FROM tags.lb_tag_radio
                        WHERE recording_mbid IN %s'''

            curs.execute(query, (mbids,))
            output = []
            while True:
                row = curs.fetchone()
                if not row:
                    break

                output.append(BulkTagLookupOutput(**row))

        return output
