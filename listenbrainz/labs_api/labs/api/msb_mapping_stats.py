import json
from operator import itemgetter

import psycopg2
import psycopg2.extras
from flask import current_app
from datasethoster import Query


class MSBMappingStatsQuery(Query):

    def names(self):
        return ("msb-mapping-stats", "MSB mapping stats")

    def inputs(self):
        return ['num_entries']

    def introduction(self):
        return """See the latest X stats entries for the MSB Mapping"""

    def outputs(self):
        return ['stats_json', 'created']

    def fetch(self, params, count=-1, offset=-1):

        with psycopg2.connect(current_app.config['MB_DATABASE_URI']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

                query = """SELECT stats AS stats_json,
                                  created
                             FROM mapping.mapping_stats
                         ORDER BY created DESC"""
                args = []
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

                    r = dict(row)
                    r['stats_json'] = json.dumps(r['stats_json'], sort_keys=True, indent=4)
                    output.append(r)

                return output
