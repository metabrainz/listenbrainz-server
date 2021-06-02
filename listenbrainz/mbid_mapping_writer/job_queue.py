from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
from queue import PriorityQueue, Queue, Empty
from time import time
import threading
import traceback

from flask import current_app
import sqlalchemy
from listenbrainz.db import timescale
from listenbrainz.mbid_mapping_writer.matcher import lookup_new_listens
from listenbrainz.labs_api.labs.api.mbid_mapping import MATCH_TYPES
from listenbrainz.utils import init_cache
from brainzutils import metrics, cache

MAX_THREADS = 1
MAX_QUEUED_JOBS = MAX_THREADS * 2
MSID_FETCH_BATCH_SIZE = 1000
UPDATE_INTERVAL = 60 


@dataclass(order=True)
class JobItem:
    priority: int
    item: object = field()


class MappingJobQueue(threading.Thread):

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.done = False
        self.app = app
        self.queue = PriorityQueue()

        init_cache(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], namespace=app.config['REDIS_NAMESPACE'])
        metrics.init("listenbrainz")

    def add_new_listens(self, listens):
        self.queue.put(JobItem(1, listens))

    def terminate(self):
        self.done = True
        self.join()

    def add_unmatched_listen_msids_to_queue(self):

        msids = []
        query = """SELECT data->'track_metadata'->'additional_info'->>'recording_msid' as recording_msid
                     FROM listen
                LEFT JOIN listen_mbid_mapping mbid
                       ON data->'track_metadata'->'additional_info'->>'recording_msid' = mbid.recording_mbid::text
                    WHERE mbid.recording_mbid is null
                 ORDER BY listened_at desc
                    LIMIT :limit"""

        with timescale.engine.connect() as connection:
            curs = connection.execute(sqlalchemy.text(query), limit=MSID_FETCH_BATCH_SIZE)
            while True:
                result = curs.fetchone()
                if not result:
                    break

                self.queue.put(JobItem(0, result[0]))
                msids.append(result[0])

        return msids


    def run(self):
        self.app.logger.info("start job queue thread")

        stats = { "processed": 0, "total": 0, "errors": 0 }
        for typ in MATCH_TYPES:
            stats[typ] = 0

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


        update_time = time() + UPDATE_INTERVAL
        try:
            with self.app.app_context():
                with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                    futures = {}
                    while not self.done:

                        completed, uncompleted = wait(futures, return_when=FIRST_COMPLETED)
                        for complete in completed:
                            exc = complete.exception()
                            if exc:
                                self.app.logger.error(exc)
                                stats["errors"] += 1
                            else:
                                job_stats = complete.result()
                                for stat in job_stats:
                                    stats[stat] += job_stats[stat]
                            del futures[complete]

                        for i in range(MAX_QUEUED_JOBS - len(uncompleted)):
                            try:
                                job = self.queue.get(False)
                            except Empty:
                                break

                            if job[0] > 0:
                                futures[executor.submit(lookup_new_listens, self.app, job[1])] = job[0]
                            else:
                                self.app.logger.info("Unsupported job type in MappingJobQueue (MBID Mapping Writer).")
                        if time() > update_time: 
                            update_time = time() + UPDATE_INTERVAL
                            if stats["total"] != 0:
                                percent = (stats["exact_match"] + stats["high_quality"] + stats["med_quality"] +
                                          stats["low_quality"]) / stats["total"] * 100.00
                                self.app.logger.info("%d (%d) listens: exact %d high %d med %d low %d no %d err %d %.1f%%" %
                                        (stats["total"], stats["processed"], stats["exact_match"], stats["high_quality"],
                                         stats["med_quality"], stats["low_quality"], stats["no_match"], 
                                         stats["errors"], percent))
                                metrics.set("listenbrainz-mbid-mapping-writer", 
                                            total_match_p=percent,
                                            exact_match_p=stats["exact_match"] / stats["total"] * 100.00, 
                                            high_quality_p=stats["high_quality"] / stats["total"] * 100.00,
                                            med_quality_p=stats["med_quality"] / stats["total"] * 100.00,
                                            low_quality_p=stats["low_quality"] / stats["total"] * 100.00,
                                            no_match_p=stats["no_match"] / stats["total"] * 100.00,
                                            errors_p=stats["errors"] / stats["total"] * 100.00,
                                            total_listens=stats["total"],
                                            total_processed=stats["processed"],
                                            exact_match=stats["exact_match"],
                                            high_quality=stats["high_quality"],
                                            med_quality=stats["med_quality"],
                                            low_quality=stats["low_quality"],
                                            no_match=stats["no_match"],
                                            errors=stats["errors"])
                            

        except Exception as err:
            self.app.logger.info(traceback.format_exc())

        self.app.logger.info("job queue thread finished")
