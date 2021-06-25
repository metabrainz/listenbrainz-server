from operator import itemgetter

import sqlalchemy
import psycopg2
from psycopg2.extras import execute_values
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery, MATCH_TYPES, MATCH_TYPE_NO_MATCH, MATCH_TYPE_EXACT_MATCH
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery
from listenbrainz.db import timescale


MAX_THREADS = 2
MAX_QUEUED_JOBS = MAX_THREADS * 2
SEARCH_TIMEOUT = 3600  # basically, don't have searches timeout.


def process_listens(app, listens, is_legacy_listen=False):
    """Given a set of listens, look up each one and then save the results to
       the DB. Note: Legacy listens to not need to be checked to see if
       a result alrady exists in the DB -- the selection of legacy listens
       has already taken care of this."""
       

    stats = {"processed": 0, "total": 0, "errors": 0, "legacy_match": 0}
    for typ in MATCH_TYPES:
        stats[typ] = 0

    skipped = 0

    msids = {str(listen['recording_msid']): listen for listen in listens}
    stats["total"] = len(msids)
    if len(msids):
        if not is_legacy_listen:
            with timescale.engine.connect() as connection:
                query = """SELECT recording_msid 
                             FROM listen_mbid_mapping
                            WHERE recording_msid IN :msids"""
                curs = connection.execute(sqlalchemy.text(
                    query), msids=tuple(msids.keys()))
                while True:
                    result = curs.fetchone()
                    if not result:
                        break
                    del msids[str(result[0])]
                    stats["processed"] += 1
                    skipped += 1
        else:
            stats["processed"] += len(msids)

        conn = timescale.engine.raw_connection()
        with conn.cursor() as curs:
            try:
                # Try an exact lookup (in postgres) first.
                matches, remaining_listens, stats = lookup_listens(
                    app, list(msids.values()), stats, True)

                # For all remaining listens, do a fuzzy lookup.
                if remaining_listens:
                    new_matches, remaining_listens, stats = lookup_listens(
                        app, remaining_listens, stats, False)
                    matches.extend(new_matches)

                    # For all listens that are not matched, enter a no match entry, so we don't 
                    # keep attempting to look up more listens.
                    for listen in remaining_listens:
                        matches.append(
                            (listen['recording_msid'], None, None, None, None, None, MATCH_TYPES[0]))
                        stats['no_match'] += 1

                stats["processed"] += len(matches)
                if is_legacy_listen:
                    stats["legacy_match"] += len(matches)

                # Finally insert matches to PG
                query = """INSERT INTO listen_mbid_mapping (recording_msid, recording_mbid, release_mbid, artist_credit_id,
                                                            artist_credit_name, recording_name, match_type)
                                VALUES %s
                           ON CONFLICT DO NOTHING"""
                execute_values(curs, query, matches, template=None)

            except psycopg2.OperationalError as err:
                app.logger.info(
                    "Cannot insert MBID mapping rows. (%s)" % str(err))
                conn.rollback()
                return

        conn.commit()

    return stats


def lookup_listens(app, listens, stats, exact):
    """ Attempt an exact string lookup on the passed in listens. Return the maches and the
        listens that were NOT matched. if exact == True, use an exact PG lookup otherwise
        use a typesense fuzzy lookup.
    """

    if len(listens) == 0:
        return ([], [], stats)

    if exact:
        q = ArtistCreditRecordingLookupQuery()
    else:
        q = MBIDMappingQuery(timeout=SEARCH_TIMEOUT, remove_stop_words=True)

    params = []
    for listen in listens:
        params.append({'[artist_credit_name]': listen["data"]["artist_name"],
                       '[recording_name]': listen["data"]["track_name"]})

    rows = []
    hits = q.fetch(params)
    for hit in sorted(hits, key=itemgetter("index"), reverse=True):
        listen = listens[hit["index"]]
        if exact:
            hit["match_type"] = MATCH_TYPE_EXACT_MATCH
        stats[MATCH_TYPES[hit["match_type"]]] += 1
        rows.append((listen['recording_msid'],
                     hit["recording_mbid"],
                     hit["release_mbid"],
                     hit["artist_credit_id"],
                     hit["artist_credit_name"],
                     hit["recording_name"],
                     MATCH_TYPES[hit["match_type"]]))

        listens.pop(hit["index"])
        if len(listens) == 0:
            break

    return rows, listens, stats
