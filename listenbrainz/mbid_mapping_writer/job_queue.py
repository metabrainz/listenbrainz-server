from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
import datetime
from queue import PriorityQueue, Queue, Empty
from typing import Any
from time import monotonic, sleep
import threading
import traceback
from io import StringIO

from flask import current_app
import sqlalchemy
from sqlalchemy import text

from listenbrainz.listen import Listen
from listenbrainz.db import timescale
from listenbrainz.listenstore import LISTEN_MINIMUM_DATE
from listenbrainz.mbid_mapping_writer.matcher import process_listens
from listenbrainz.mbid_mapping_writer.mbid_mapper import MATCH_TYPES
from listenbrainz.utils import init_cache
from listenbrainz.listenstore.timescale_listenstore import DATA_START_YEAR_IN_SECONDS, EPOCH
from listenbrainz import messybrainz as msb_db
from brainzutils import metrics, cache

MAX_THREADS = 3
MAX_QUEUED_JOBS = MAX_THREADS * 2
QUEUE_RELOAD_THRESHOLD = 0
UPDATE_INTERVAL = 30

LEGACY_LISTEN = 2
RECHECK_LISTEN = 1
NEW_LISTEN = 0

# How long to wait if all unmatched listens have been processed before starting the process anew
UNMATCHED_LISTENS_COMPLETED_TIMEOUT = 86400  # in s

# This is the point where the legacy listens should be processed from
LEGACY_LISTENS_LOAD_WINDOW = datetime.timedelta(days=3)
LEGACY_LISTENS_INDEX_DATE_CACHE_KEY = "mbid.legacy_index_date"

# How many listens should be re-checked every mapping pass?
NUM_ITEMS_TO_RECHECK_PER_PASS = 100000

# When looking for mapped items marked for re-checking, use this batch size
RECHECK_BATCH_SIZE = 5000


@dataclass(order=True)
class JobItem:
    priority: int
    item: Any = field(compare=False)


def _add_legacy_listens_to_queue(obj):
    return obj.add_legacy_listens_to_queue()


class MappingJobQueue(threading.Thread):
    """ This class coordinates incoming listens and legacy listens, giving
        priority to new and incoming listens. Threads are fired off as needed
        looking up jobs in the background and then this main matcher
        thread can deal with the statstics and reporting"""

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.done = False
        self.app = app
        self.queue = PriorityQueue()
        self.unmatched_listens_complete_time = 0
        self.legacy_load_thread = None
        self.legacy_next_run = 0
        self.legacy_listens_index_date = None
        self.num_legacy_listens_loaded = 0
        self.last_processed = 0

        init_cache(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'],
                   namespace=app.config['REDIS_NAMESPACE'])
        metrics.init("listenbrainz")
        self.load_legacy_listens()

    def add_new_listens(self, listens):
        self.queue.put(JobItem(NEW_LISTEN, listens))

    def terminate(self):
        self.done = True
        self.join()

    def mark_oldest_no_match_entries_as_stale(self):
        """
            THIS FUNCTION IS CURRENTLY UNUSED, BUT WILL BE USED LATER.
        """
        query = """UPDATE mbid_mapping
                      SET last_updated = '1970-01-01'
                    WHERE match_type = 'no_match'
                      AND last_updated >= (SELECT last_updated
                                             FROM mbid_mapping
                                            WHERE match_type = 'no_match'
                                         ORDER BY last_updated
                                           OFFSET %s
                                            LIMIT 1);"""
        args = (NUM_ITEMS_TO_RECHECK_PER_PASS,)

    def load_legacy_listens(self):
        """ This function should kick off a thread to load more legacy listens if called.
            It may be called multiple times, so it must guard against firing off multiple
            threads. """

        if self.legacy_load_thread or (self.legacy_next_run and self.legacy_next_run > monotonic()):
            return

        self.legacy_load_thread = threading.Thread(
            target=_add_legacy_listens_to_queue, args=(self,))
        self.legacy_load_thread.start()

    def fetch_and_queue_listens(self, query, args, priority):
        """ Fetch and queue legacy and recheck listens """

        msb_query = """SELECT gid AS recording_msid
                            , recording AS track_name
                            , artist_credit AS artist_name
                         FROM messybrainz.submissions
                       WHERE gid in :msids"""

        count = 0
        msids = []
        with timescale.engine.connect() as connection:
            curs = connection.execute(text(query), args)
            for row in curs.fetchall():
                msids.append(row.recording_msid)

        if len(msids) == 0:
            return 0

        with timescale.engine.connect() as connection:
            curs = connection.execute(text(msb_query), {"msids": tuple(msids)})
            while True:
                result = curs.fetchone()
                if not result:
                    break

                self.queue.put(JobItem(priority, [
                    {
                        "track_metadata": {
                            "artist_name": result[2],
                            "track_name": result[1]
                        },
                        "recording_msid": result[0],
                        "priority": priority
                    }
                ]))
                count += 1

        return count

    def add_legacy_listens_to_queue(self):
        """Fetch more legacy listens from the listens table by doing an left join
           on the matched listens, finding the next chunk of legacy listens to look up.
           Listens are added to the queue with a low priority."""

        # Find listens that have no entry in the mapping yet.
        legacy_query = """SELECT l.recording_msid::TEXT AS recording_msid
                            FROM listen l
                       LEFT JOIN mbid_mapping m
                              ON l.recording_msid = m.recording_msid
                           WHERE m.recording_mbid IS NULL
                             AND listened_at <= :max_ts
                             AND listened_at > :min_ts"""

        # Find mapping rows that need to be rechecked
        recheck_query = """SELECT recording_msid
                             FROM mbid_mapping
                            WHERE last_updated = '1970-01-01'
                               OR check_again <= NOW()
                               OR (check_again IS NULL AND recording_mbid IS NULL)
                         ORDER BY check_again NULLS FIRST
                            LIMIT %d
                            """ % RECHECK_BATCH_SIZE

        # Check to see where we need to pick up from, or start new
        if not self.legacy_listens_index_date:
            dt = cache.get(LEGACY_LISTENS_INDEX_DATE_CACHE_KEY, decode=False) or b""
            try:
                self.legacy_listens_index_date = datetime.datetime.strptime(str(dt, "utf-8"), "%Y-%m-%d")
                self.app.logger.info("Loaded date index from cache: %s %s" % (
                    self.legacy_listens_index_date, str(dt)))
            except ValueError:
                self.legacy_listens_index_date = datetime.datetime.now()
                self.app.logger.info("Use date index now()")

        # Check to see if we're done
        if self.legacy_listens_index_date < LISTEN_MINIMUM_DATE - LEGACY_LISTENS_LOAD_WINDOW:
            self.app.logger.info("Finished looking up all legacy listens! Wooo!")
            self.legacy_next_run = monotonic() + UNMATCHED_LISTENS_COMPLETED_TIMEOUT
            self.legacy_listens_index_date = datetime.datetime.now()
            self.num_legacy_listens_loaded = 0
            cache.set(
                LEGACY_LISTENS_INDEX_DATE_CACHE_KEY,
                self.legacy_listens_index_date.strftime("%Y-%m-%d"),
                expirein=0,
                encode=False
            )

            return

        # Check to see if any listens have been marked for re-check
        count = self.fetch_and_queue_listens(recheck_query, {}, RECHECK_LISTEN)
        if count > 0:
            self.app.logger.info("Loaded %d listens to be rechecked." % count)
            return
        else:
            # If none, check for old legacy listens
            count = self.fetch_and_queue_listens(legacy_query, {
                "max_ts": self.legacy_listens_index_date,
                "min_ts": self.legacy_listens_index_date - LEGACY_LISTENS_LOAD_WINDOW
            }, LEGACY_LISTEN)
            self.app.logger.info("Loaded %s more legacy listens for %s" %
                                 (count, self.legacy_listens_index_date.strftime("%Y-%m-%d")))

        # update cache entry and count
        self.legacy_listens_index_date -= LEGACY_LISTENS_LOAD_WINDOW
        cache.set(
            LEGACY_LISTENS_INDEX_DATE_CACHE_KEY,
            self.legacy_listens_index_date.strftime("%Y-%m-%d"),
            expirein=0,
            encode=False
        )
        self.num_legacy_listens_loaded = count

    def update_metrics(self, stats):
        """ Calculate stats and print status to stdout and report metrics."""

        if stats["total"] != 0:
            if self.last_processed:
                listens_per_sec = int(
                    (stats["processed"] - self.last_processed) / UPDATE_INTERVAL)
            else:
                listens_per_sec = 0
            self.last_processed = stats["processed"]

            percent = (stats["exact_match"] + stats["high_quality"] + stats["med_quality"] +
                       stats["low_quality"]) / stats["total"] * 100.00
            self.app.logger.info("total %d matched %d/%d legacy: %d queue: %d %d l/s" %
                                 (stats["total"],
                                  stats["exact_match"] + stats["high_quality"] + stats["med_quality"] + stats["low_quality"],
                                  stats["no_match"],
                                  stats["legacy"],
                                  self.queue.qsize(),
                                  listens_per_sec))

            if stats["last_exact_match"] is None:
                stats["last_exact_match"] = stats["exact_match"]
                stats["last_high_quality"] = stats["high_quality"]
                stats["last_med_quality"] = stats["med_quality"]
                stats["last_low_quality"] = stats["low_quality"]
                stats["last_no_match"] = stats["no_match"]
            metrics.set("listenbrainz-mbid-mapping-writer",
                        total_match_p=percent,
                        exact_match_p=stats["exact_match"] /
                        stats["total"] * 100.00,
                        high_quality_p=stats["high_quality"] /
                        stats["total"] * 100.00,
                        med_quality_p=stats["med_quality"] /
                        stats["total"] * 100.00,
                        low_quality_p=stats["low_quality"] /
                        stats["total"] * 100.00,
                        no_match_p=stats["no_match"] / stats["total"] * 100.00,
                        errors_p=stats["errors"] / stats["total"] * 100.00,
                        total_listens=stats["total"],
                        exact_match=stats["exact_match"],
                        high_quality=stats["high_quality"],
                        med_quality=stats["med_quality"],
                        low_quality=stats["low_quality"],
                        no_match=stats["no_match"],
                        errors=stats["errors"],
                        qsize=self.queue.qsize(),
                        exact_match_rate=stats["exact_match"] - stats["last_exact_match"],
                        high_quality_rate=stats["high_quality"] - stats["last_high_quality"],
                        med_quality_rate=stats["med_quality"] - stats["last_med_quality"],
                        low_quality_rate=stats["low_quality"] - stats["last_low_quality"],
                        no_match_rate=stats["no_match"] - stats["last_no_match"],
                        listens_per_sec=listens_per_sec,
                        listens_matched_p=stats["listens_matched"] / (stats["listen_count"] or .000001) * 100.0,
                        legacy_index_date=self.legacy_listens_index_date.strftime("%Y-%m-%d"))

            stats["last_exact_match"] = stats["exact_match"]
            stats["last_high_quality"] = stats["high_quality"]
            stats["last_med_quality"] = stats["med_quality"]
            stats["last_low_quality"] = stats["low_quality"]
            stats["last_no_match"] = stats["no_match"]
            stats["listens_matched"] = 0
            stats["listen_count"] = 0


    def run(self):
        """ main thread entry point"""

        stats = {"processed": 0,
                 "total": 0,
                 "errors": 0,
                 "listen_count": 0,
                 "listens_matched": 0,
                 "legacy": 0,
                 "legacy_match": 0,
                 "last_exact_match": None,
                 "last_high_quality": None,
                 "last_med_quality": None,
                 "last_low_quality": None,
                 "last_no_match": None}
        for typ in MATCH_TYPES:
            stats[typ] = 0

        # Fetch stats of how many items have already been matched.
        with timescale.engine.connect() as connection:
            query = """SELECT COUNT(*), match_type
                         FROM mbid_mapping
                     GROUP BY match_type"""
            curs = connection.execute(text(query))
            while True:
                result = curs.fetchone()
                if not result:
                    break

                stats[result[1]] = result[0]

            query = """SELECT COUNT(*)
                         FROM mbid_mapping_metadata"""
            curs = connection.execute(text(query))
            while True:
                result = curs.fetchone()
                if not result:
                    break

                stats["processed"] = result[0]
                stats["total"] = result[0]

        # the main thread loop
        update_time = monotonic() + UPDATE_INTERVAL
        try:
            with self.app.app_context():
                with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                    futures = {}
                    while not self.done:
                        completed, uncompleted = wait(
                            futures, return_when=FIRST_COMPLETED)

                        # Check for completed threads and reports errors if any occurred
                        for complete in completed:
                            exc = complete.exception()
                            if exc:
                                self.app.logger.error("Error in listen mbid mapping writer:", exc_info=exc)
                                stats["errors"] += 1
                            else:
                                job_stats = complete.result()
                                for stat in job_stats or []:
                                    stats[stat] += job_stats[stat]
                            del futures[complete]

                        # Check to see if more legacy listens need to be loaded
                        for i in range(MAX_QUEUED_JOBS - len(uncompleted)):
                            try:
                                job = self.queue.get(False)
                            except Empty:
                                sleep(.1)
                                continue

                            futures[executor.submit(
                                process_listens, self.app, job.item, job.priority)] = job.priority
                            if job.priority == LEGACY_LISTEN:
                                stats["legacy"] += 1

                        if self.legacy_load_thread and not self.legacy_load_thread.is_alive():
                            self.legacy_load_thread = None

                        if self.queue.qsize() == 0:
                            self.load_legacy_listens()

                        if monotonic() > update_time:
                            update_time = monotonic() + UPDATE_INTERVAL
                            self.update_metrics(stats)

        except Exception as err:
            self.app.logger.info(traceback.format_exc())

        self.app.logger.info("job queue thread finished")
