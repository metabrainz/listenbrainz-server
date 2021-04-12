import sqlalchemy
import psycopg2
import psycopg2.extras import execute_values
from flask import current_app
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery, MATCH_TYPE_NO_MATCH
from listenbrainz.labs_api.labs.api. import MBIDMappingQuery, MATCH_TYPE_NO_MATCH
from listenbrainz.db import timescale


MAX_THREADS = 1
MAX_QUEUED_JOBS = MAX_THREADS * 2

MATCH_TYPES = ('no_match', 'low_quality', 'med_quality', 'high_quality', 'exact_match')


def lookup_new_listens(app, listens, delivery_tag):

    msids = { str(listen['recording_msid']):listen for listen in listens }
    with timescale.engine.connect() as connection:
        query = """SELECT recording_msid 
                     FROM listen_mbid_mapping
                    WHERE recording_msid IN :msids"""
        curs = connection.execute(sqlalchemy.text(query), msids=tuple(msids.keys()))
        while True:
            result = curs.fetchone()
            if not result:
                break
            del msids[str(result[0])]

    conn = timescale.engine.raw_connection() 
    with conn.cursor() as curs:
        try:
            listens = exact_lookup_listens(app, listens, curs)
            if listens:
                fuzzy_lookup_listens(app, listens, curs)

        except psycopg2.OperationalError as err:
            app.logger.info("Cannot insert MBID mapping rows. (%s)" % str(err))
            conn.rollback()
            return None

    conn.commit()



def exact_lookup_listens(app, listens, curs):
    """ Attempt an exact string lookup on the passed in listens. Insert matches using
        the passed in cursor, which has an open transaction. Return the listens that
        were NOT matched. DB Exceptions are not caught and should be handled by the caller.
    """



def fuzzy_lookup_listens(app, listens, curs):
    """ Attempt an fussy string lookup on the passed in listens. Insert matches using
        the pass in cursor, which has an open transaction. DB Exceptions are not caught
        and should be handled by the caller.
    """

    q = MBIDMappingQuery()
    params = []
    param_listens = []
    for msid in msids:
        listen = msids[msid] 
        params.append({'[artist_credit_name]': listen["data"]["artist_name"], 
                       '[recording_name]': listen["data"]["track_name"]})
        param_listens.append(listen)

    rows = []
    hits = q.fetch(params)
    for hit in hits:
        listen = param_listens[hit["index"]]
        rows.append((listen['recording_msid'],
                    hit["recording_mbid"],
                    hit["release_mbid"],
                    hit["artist_credit_id"],
                    hit["artist_credit_name"],
                    hit["recording_name"],
                    MATCH_TYPES[hit["match_type"]]))
        del msids[str(listen['recording_msid'])]

    for msid in msids:
        rows.append((listen['recording_msid'], None, None, None, None, None, MATCH_TYPES[0]))
        
        query = """INSERT INTO listen_mbid_mapping (recording_msid, recording_mbid, release_mbid, artist_credit_id,
                                                    artist_credit_name, recording_name, match_type)
                        VALUES %s
                   ON CONFLICT DO NOTHING"""
        execute_values(curs, query, rows, template=None)
