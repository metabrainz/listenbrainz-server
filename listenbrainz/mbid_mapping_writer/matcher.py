from operator import itemgetter

import sqlalchemy
import psycopg2
from psycopg2.extras import execute_values
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery, MATCH_TYPE_NO_MATCH, MATCH_TYPE_EXACT_MATCH
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery
from listenbrainz.db import timescale


MAX_THREADS = 1
MAX_QUEUED_JOBS = MAX_THREADS * 2

MATCH_TYPES = ('no_match', 'low_quality', 'med_quality', 'high_quality', 'exact_match')

def log(msg):
    with open("/tmp/matcher.log", "a") as f:
        f.write(msg + "\n")


def lookup_new_listens(app, listens):

    log("received %d listens" % len(listens))
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
            matches, listens = exact_lookup_listens(app, list(msids.values()))
            if listens:
                matches.extend(fuzzy_lookup_listens(app, listens))

            query = """INSERT INTO listen_mbid_mapping (recording_msid, recording_mbid, release_mbid, artist_credit_id,
                                                        artist_credit_name, recording_name, match_type)
                            VALUES %s
                       ON CONFLICT DO NOTHING"""
            execute_values(curs, query, matches, template=None)

        except psycopg2.OperationalError as err:
            app.logger.info("Cannot insert MBID mapping rows. (%s)" % str(err))
            conn.rollback()
            return 

    conn.commit()

def exact_lookup_listens(app, listens):
    """ Attempt an exact string lookup on the passed in listens. Return the maches and the
        listens that were NOT matched.
    """

    q = ArtistCreditRecordingLookupQuery()
    params = []
    for listen in listens:
        params.append({'[artist_credit_name]': listen["data"]["artist_name"], 
                       '[recording_name]': listen["data"]["track_name"]})

    rows = []
    hits = q.fetch(params)
    for hit in sorted(hits, itemgetter("index"), reverse=True):
        listen = listens[hit["index"]]
        rows.append((listen['recording_msid'],
                    hit["recording_mbid"],
                    hit["release_mbid"],
                    hit["artist_credit_id"],
                    hit["artist_credit_name"],
                    hit["recording_name"],
                    MATCH_TYPES[MATCH_TYPE_EXACT_MATCH]))
        listen.pop(hit["index"])

    return rows, listens

def fuzzy_lookup_listens(app, listens):
    """ Attempt a fuzzy string lookup on the passed in listens.
    """

    q = MBIDMappingQuery()
    params = []
    for listen in listens:
        params.append({'[artist_credit_name]': listen["data"]["artist_name"], 
                       '[recording_name]': listen["data"]["track_name"]})

    rows = []
    hits = q.fetch(params)
    for hit in sorted(hits, itemgetter("index"), reverse=True):
        listen = listens[hit["index"]]
        rows.append((listen['recording_msid'],
                    hit["recording_mbid"],
                    hit["release_mbid"],
                    hit["artist_credit_id"],
                    hit["artist_credit_name"],
                    hit["recording_name"],
                    MATCH_TYPES[hit["match_type"]]))
        listen.pop(hit["index"])

    for listen in listens:
        rows.append((listen['recording_msid'], None, None, None, None, None, MATCH_TYPES[0]))

    return rows
