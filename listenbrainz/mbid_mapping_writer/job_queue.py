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
from listenbrainz.listen import Listen
from listenbrainz.db import timescale
from listenbrainz.mbid_mapping_writer.matcher import process_listens
from listenbrainz.labs_api.labs.api.mbid_mapping import MATCH_TYPES
from listenbrainz.utils import init_cache
from listenbrainz.listenstore.timescale_listenstore import DATA_START_YEAR_IN_SECONDS
from brainzutils import metrics, cache

MAX_THREADS = 3
MAX_QUEUED_JOBS = MAX_THREADS * 2
QUEUE_RELOAD_THRESHOLD = 1000
UPDATE_INTERVAL = 30

LEGACY_LISTEN = 1
NEW_LISTEN = 0

# How long to wait if all unmatched listens have been processed before starting the process anew
UNMATCHED_LISTENS_COMPLETED_TIMEOUT = 86400  # in s

# This is the point where the legacy listens should be processed from
LEGACY_LISTENS_LOAD_WINDOW = 604800  # 7 days in seconds
LEGACY_LISTENS_INDEX_DATE_CACHE_KEY = "mbid.legacy_index_date"


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
        self.legacy_listens_index_date = 0
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

    def load_legacy_listens(self):
        """ This function should kick off a thread to load more legacy listens if called.
            It may be called multiple times, so it must guard against firing off multiple
            threads. """

        if self.legacy_load_thread or (self.legacy_next_run and self.legacy_next_run > monotonic()):
            return

        self.legacy_load_thread = threading.Thread(
            target=_add_legacy_listens_to_queue, args=(self,))
        self.legacy_load_thread.start()

    def add_legacy_listens_to_queue(self):
        """Fetch more legacy listens from the listens table by doing an left join
           on the matched listens, finding the next chunk of legacy listens to look up.
           Listens are added to the queue with a low priority."""

        # Check to see where we need to pick up from, or start new
        if not self.legacy_listens_index_date:
            dt = cache.get(LEGACY_LISTENS_INDEX_DATE_CACHE_KEY, decode=False) or b""
            try:
                self.legacy_listens_index_date = int(
                    datetime.datetime.strptime(str(dt, "utf-8"), "%Y-%m-%d").timestamp())
                self.app.logger.info("Loaded date index from cache: %d %s" % (
                    self.legacy_listens_index_date, str(dt)))
            except ValueError:
                self.legacy_listens_index_date = int(
                    datetime.datetime.now().timestamp())
                self.app.logger.info("Use date index now()")

        # TODO Remove this before PR
        self.legacy_listens_index_date = int( datetime.datetime.now().timestamp())

        # Check to see if we're done
        if self.legacy_listens_index_date < DATA_START_YEAR_IN_SECONDS - LEGACY_LISTENS_LOAD_WINDOW:
            self.app.logger.info(
                "Finished looking up all legacy listens! Wooo!")
            self.legacy_next_run = monotonic() + UNMATCHED_LISTENS_COMPLETED_TIMEOUT
            self.legacy_listens_index_date = int(datetime.datetime.now().timestamp())
            self.num_legacy_listens_loaded = 0
            dt = datetime.datetime.fromtimestamp(self.legacy_listens_index_date)
            cache.set(LEGACY_LISTENS_INDEX_DATE_CACHE_KEY, dt.strftime("%Y-%m-%d"), expirein=0, encode=False)
            return

        # Load listens
        self.app.logger.info("Load more legacy listens for %s" % datetime.datetime.fromtimestamp(
            self.legacy_listens_index_date).strftime("%Y-%m-%d"))
        query = """SELECT data->'track_metadata'->'additional_info'->>'recording_msid'::TEXT AS recording_msid,
                          track_name,
                          data->'track_metadata'->'artist_name' AS artist_name
                     FROM listen
                LEFT JOIN listen_join_listen_mbid_mapping lj
                       ON data->'track_metadata'->'additional_info'->>'recording_msid' = lj.recording_msid::text
                 WHERE lj.recording_msid IS NULL
                      AND listened_at <= :max_ts
                      AND listened_at > :min_ts"""

        count = 0
        with timescale.engine.connect() as connection:
            curs = connection.execute(sqlalchemy.text(query),
                                      max_ts=self.legacy_listens_index_date,
                                      min_ts=self.legacy_listens_index_date - LEGACY_LISTENS_LOAD_WINDOW)
            while True:
                result = curs.fetchone()
                if not result:
                    break

                self.queue.put(JobItem(LEGACY_LISTEN, [{"data": {"artist_name": result[2],
                                                                 "track_name": result[1]},
                                                        "recording_msid": result[0],
                                                        "legacy": True}]))
                count += 1

        # update cache entry and count
        self.legacy_listens_index_date -= LEGACY_LISTENS_LOAD_WINDOW
        dt = datetime.datetime.fromtimestamp(self.legacy_listens_index_date)
        cache.set(LEGACY_LISTENS_INDEX_DATE_CACHE_KEY, dt.strftime("%Y-%m-%d"), expirein=0, encode=False)
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
            self.app.logger.info("loaded %d processed %d matched %d not %d legacy: %d queue: %d %d l/s" %
                                 (stats["total"], stats["processed"], stats["exact_match"] + stats["high_quality"] +
                                  stats["med_quality"] +
                                  stats["low_quality"], stats["no_match"],
                                     stats["legacy"], self.queue.qsize(), listens_per_sec))

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
                        total_processed=stats["processed"],
                        exact_match=stats["exact_match"],
                        high_quality=stats["high_quality"],
                        med_quality=stats["med_quality"],
                        low_quality=stats["low_quality"],
                        no_match=stats["no_match"],
                        errors=stats["errors"],
                        legacy=stats["legacy"],
                        legacy_match=stats["legacy_match"],
                        qsize=self.queue.qsize(),
                        listens_per_sec=listens_per_sec,
                        legacy_index_date=datetime.date.fromtimestamp(self.legacy_listens_index_date).strftime("%Y-%m-%d"))

    def run(self):
        """ main thread entry point"""

        stats = {"processed": 0, "total": 0,
                 "errors": 0, "legacy": 0, "legacy_match": 0}
        for typ in MATCH_TYPES:
            stats[typ] = 0

        # Fetch stats of how many items have already been matched.
        with timescale.engine.connect() as connection:
            query = """SELECT COUNT(*), match_type
                         FROM listen_mbid_mapping
                     GROUP BY match_type"""
            curs = connection.execute(query)
            while True:
                result = curs.fetchone()
                if not result:
                    break

                stats[result[1]] = result[0]

            query = """SELECT COUNT(*)
                         FROM listen_mbid_mapping"""
            curs = connection.execute(query)
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
                                f = StringIO()
                                traceback.print_exception(
                                    None, exc, exc.__traceback__, limit=None, file=f)
                                f.seek(0)
                                self.app.logger.error(f.read())
                                stats["errors"] += 1
                            else:
                                job_stats = complete.result()
                                for stat in job_stats:
                                    stats[stat] += job_stats[stat]
                            del futures[complete]

                        # Check to see if more legacy listens need to be loaded
                        for i in range(MAX_QUEUED_JOBS - len(uncompleted)):
                            try:
                                job = self.queue.get(False)
                                if self.queue.qsize() < QUEUE_RELOAD_THRESHOLD:
                                    self.load_legacy_listens()
                            except Empty:
                                sleep(.1)
                                continue

                            futures[executor.submit(
                                process_listens, self.app, job.item, job.priority == LEGACY_LISTEN)] = job.priority
                            if job.priority == LEGACY_LISTEN:
                                stats["legacy"] += 1

                        if self.legacy_load_thread and not self.legacy_load_thread.is_alive():
                            self.legacy_load_thread = None
                            self.app.logger.info(
                                "%d legacy listens loaded" % self.num_legacy_listens_loaded)

                        if monotonic() > update_time:
                            update_time = monotonic() + UPDATE_INTERVAL
                            self.update_metrics(stats)

        except Exception as err:
            self.app.logger.info(traceback.format_exc())

        self.app.logger.info("job queue thread finished")
