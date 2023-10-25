from flask import current_app
from werkzeug.exceptions import BadRequest
import psycopg2
import psycopg2.extras

from datasethoster import Query


class BulkTagLookup(Query):
    '''
        Look up a tag and popularity data for a list of recordings, based on MBID. 
    '''

    def names(self):
        return ("bulk-tag-lookup", "Bulk MusicBrainz Tag/Popularity by recording MBID Lookup")

    def inputs(self):
        return ['[recording_mbid]']

    def introduction(self):
        return """Look up tag and popularity information given a recording MBID"""

    def outputs(self):
        return ['recording_mbid', 'tag', 'percent', 'source']

    def fetch(self, params, offset=-1, count=-1):

        mbids = tuple([psycopg2.extensions.adapt(p['[recording_mbid]']) for p in params])
        if len(mbids) > 1000:
            raise BadRequest("Cannot lookup more than 1,000 recordings at a time.")

        with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                query = '''SELECT recording_mbid
                                , tag
                                , percent
                                , source
                             FROM tags.lb_tag_radio
                            WHERE recording_mbid IN %s'''

                curs.execute(query, tuple([mbids]))
                output = []
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    output.append(dict(row))

        return output
