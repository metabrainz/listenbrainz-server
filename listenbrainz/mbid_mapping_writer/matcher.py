import uuid
from operator import itemgetter

import sqlalchemy
import psycopg2
from flask import current_app
from psycopg2.extras import execute_values
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery
from listenbrainz.mbid_mapping_writer.mbid_mapper import MATCH_TYPES, MATCH_TYPE_NO_MATCH, MATCH_TYPE_EXACT_MATCH
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery
from listenbrainz.db import timescale


MAX_THREADS = 2
MAX_QUEUED_JOBS = MAX_THREADS * 2
SEARCH_TIMEOUT = 3600  # basically, don't have searches timeout.


def process_listens(app, listens, priority):
    """Given a set of listens, look up each one and then save the results to
       the DB. Note: Legacy listens to not need to be checked to see if
       a result alrady exists in the DB -- the selection of legacy listens
       has already taken care of this."""

    from listenbrainz.mbid_mapping_writer.job_queue import NEW_LISTEN, RECHECK_LISTEN

    stats = {"processed": 0, "total": 0, "errors": 0, "listen_count": 0, "listens_matched": 0}
    for typ in MATCH_TYPES:
        stats[typ] = 0

    msids = {str(listen['recording_msid']): listen for listen in listens}
    stats["total"] = len(msids)
    if priority == NEW_LISTEN:
        stats["listen_count"] += len(msids)

    # To debug the mapping, set this to True or a specific priority
    # e.g. (priority == RECHECK_LISTEN)
    debug = False

    if len(msids) == 0:
        return stats

    listens_to_check = []

    # Remove msids for which we already have a match, unless its timestamp is 0
    # or if the msid was last checked more than 2 weeks ago and no match was
    # found at that time, which means we should re-check the item
    with timescale.engine.connect() as connection:
        query = """
            SELECT t.recording_msid
                 , mm.match_type
        -- unable to use values here because sqlachemy having trouble to pass list/tuple to values clause
              FROM unnest(:msids) AS t(recording_msid)
         LEFT JOIN mbid_mapping mm
                ON t.recording_msid::uuid = mm.recording_msid
             WHERE mm.last_updated = '1970-01-01'  -- msid marked for rechecking manually
                OR mm.check_again <= NOW()     -- msid not found last time, marked for rechecking
                OR mm.recording_msid IS NULL   -- msid seen for first time
        """
        curs = connection.execute(sqlalchemy.text(query), msids=list(msids.keys()))
        msids_to_check = curs.fetchall()

        rem_msids = []
        for row in msids_to_check:
            rem_msids.append(row['recording_msid'])
            listen = msids[row['recording_msid']]
            listens_to_check.append(listen)

            if row['match_type']:
                stats["listens_matched"] += 1

        stats["processed"] += len(msids_to_check)

        if debug:
            for msid in msids:
                if msid not in msids_to_check:
                    app.logger.info(f"Remove {msid}, since a match exists")

    if len(listens_to_check) == 0:
        return stats

    conn = timescale.engine.raw_connection()
    with conn.cursor() as curs:
        try:
            # Try an exact lookup (in postgres) first.
            matches, remaining_listens, stats = lookup_listens(
                app, listens_to_check, stats, True, debug)

            # For all remaining listens, do a fuzzy lookup.
            if remaining_listens:
                new_matches, remaining_listens, stats = lookup_listens(
                    app, remaining_listens, stats, False, debug)
                matches.extend(new_matches)

            if priority == NEW_LISTEN:
                stats["listens_matched"] += len(matches)

            # For all listens that are not matched, enter a no match entry, so we don't
            # keep attempting to look up more listens.
            for listen in remaining_listens:
                matches.append((listen['recording_msid'], None, None, None, None, None, None, None, MATCH_TYPES[0]))
                stats['no_match'] += 1

            stats["processed"] += len(matches)

            metadata_query = """
                INSERT INTO mbid_mapping_metadata AS mbid
                          ( recording_mbid
                          , release_mbid
                          , release_name
                          , artist_mbids
                          , artist_credit_id
                          , artist_credit_name
                          , recording_name
                          , last_updated
                          )
                     VALUES
                          ( %s::UUID
                          , %s::UUID
                          , %s
                          , %s::UUID[]
                          , %s
                          , %s
                          , %s
                          , now()
                          )
                ON CONFLICT (recording_mbid) DO UPDATE
                        SET release_mbid = EXCLUDED.release_mbid
                          , release_name = EXCLUDED.release_name
                          , artist_mbids = EXCLUDED.artist_mbids
                          , artist_credit_id = EXCLUDED.artist_credit_id
                          , artist_credit_name = EXCLUDED.artist_credit_name
                          , recording_name = EXCLUDED.recording_name
                          , last_updated = now()
            """

            mapping_query = """
                INSERT INTO mbid_mapping AS m(recording_msid, recording_mbid, match_type, last_updated, check_again)
                     VALUES (
                            %(recording_msid)s::UUID
                          , %(recording_mbid)s::UUID
                          , %(match_type)s
                          , now()
                          -- inserting msid for first time, check again with gap of 1 day
                          , CASE %(match_type)s WHEN 'no_match' THEN now() + INTERVAL '1 day' ELSE NULL END
                            )
                ON CONFLICT (recording_msid) DO UPDATE
                        SET recording_msid = EXCLUDED.recording_msid
                          , recording_mbid = EXCLUDED.recording_mbid
                          , match_type = EXCLUDED.match_type
                          , last_updated = now()
                          -- rechecked msid already, if still no match found then check again after twice the previous interval time
                          , check_again = CASE EXCLUDED.match_type WHEN 'no_match' THEN now() + least((m.check_again - m.last_updated) * 2, INTERVAL '32 days') ELSE NULL END
            """

            # Finally insert matches to PG
            for match in matches:
                # Insert/update the metadata row
                if match[1] is not None:
                    curs.execute(metadata_query, match[1:8])

                # Insert the mapping row
                curs.execute(
                    mapping_query,
                    {"recording_msid": match[0], "recording_mbid": match[1], "match_type": match[8]}
                )

        except psycopg2.errors.CardinalityViolation:
            app.logger.error("CardinalityViolation on insert to mbid mapping\n%s" % str(query))
            conn.rollback()
            return

        except (psycopg2.OperationalError, psycopg2.errors.DatatypeMismatch) as err:
            app.logger.info("Cannot insert MBID mapping rows. (%s)" % str(err))
            conn.rollback()
            return

    conn.commit()

    return stats


def lookup_listens(app, listens, stats, exact, debug):
    """ Attempt an exact string lookup on the passed in listens. Return the maches and the
        listens that were NOT matched. if exact == True, use an exact PG lookup otherwise
        use a typesense fuzzy lookup.
    """
    if len(listens) == 0:
        return ([], [], stats)

    if debug:
        app.logger.info(f"""Lookup (exact {exact}) '{listens[0]["data"]["artist_name"]}', '{listens[0]["data"]["track_name"]}'""")

    if exact:
        q = ArtistCreditRecordingLookupQuery(debug=debug)
    else:
        q = MBIDMappingQuery(timeout=SEARCH_TIMEOUT, remove_stop_words=True, debug=debug)

    params = []
    for listen in listens:
        params.append({'[artist_credit_name]': listen["track_metadata"]["artist_name"],
                       '[recording_name]': listen["track_metadata"]["track_name"]})

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
                     hit["release_name"],
                     hit["artist_mbids"],
                     hit["artist_credit_id"],
                     hit["artist_credit_name"],
                     hit["recording_name"],
                     MATCH_TYPES[hit["match_type"]]))

        if debug:
            app.logger.info("\n".join(q.get_debug_log_lines()))

        listens.pop(hit["index"])
        if len(listens) == 0:
            break

    else:
        if debug:
            app.logger.info("No matches returned.")

    return rows, listens, stats
