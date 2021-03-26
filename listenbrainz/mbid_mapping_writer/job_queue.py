from  concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from queue import PriorityQueue, Queue, Empty
import threading
from time import sleep
import traceback

import sqlalchemy
import psycopg2
from psycopg2.extras import execute_values
from flask import current_app
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_PLAYING_NOW
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery, MATCH_TYPE_NO_MATCH
from listenbrainz.db import timescale

MAX_THREADS = 4
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
        
    conn = timescale.engine.raw_connection() 
    with conn.cursor() as curs:
        query = """INSERT INTO listen_mbid_mapping (recording_msid, recording_mbid, release_mbid, artist_credit_id,
                                                    artist_credit_name, recording_name, match_type)
                        VALUES %s
                   ON CONFLICT DO NOTHING"""
        try:
            execute_values(curs, query, rows, template=None)
        except psycopg2.OperationalError as err:
            app.logger.info("Cannot insert MBID mapping rows. (%s)" % str(err))
            conn.rollback()
            return None

    conn.commit()

    return delivery_tag


class MappingJobQueue(threading.Thread):

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.done = False
        self.app = app
        self.queue = PriorityQueue()
        self.delivery_tag_queue = Queue()
        self.priority = 1

    def get_completed_delivery_tags(self):

        tags = []
        while True:
            try:
                tag = self.delivery_tag_queue.get(False)
            except Empty:
                break

            tags.append(tag)

        return tags

    def add_new_listens(self, listens, delivery_tag):
        self.queue.put((self.priority, listens, delivery_tag))
        self.priority += 1

    def terminate(self):
        self.done = True
        self.join()

    def run(self):
        self.app.logger.info("start job queue thread")

        try:
            with self.app.app_context():
                with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                    futures = {}
                    while not self.done:

                        completed, uncompleted = wait(futures, return_when=FIRST_COMPLETED)
                        for complete in completed:
                            exc = complete.exception()
                            if exc:
                                self.app.logger.info("job %s failed" % futures[complete])
                                # TODO: What happens to items that fail??
                                self.app.logger.error("\n".join(traceback.format_exception(None, exc, exc.__traceback__)))
                            else:
                                self.app.logger.info("job %s complete" % futures[complete])
                                self.delivery_tag_queue.put(complete.result())
                            del futures[complete]

                        for i in range(MAX_QUEUED_JOBS - len(uncompleted)):
                            try:
                                job = self.queue.get(False)
                            except Empty:
                                break

                            if job[0] > 0:
                                futures[executor.submit(lookup_new_listens, self.app, job[1], job[2])] = job[0]
                            else:
                                self.app.logger.info("Unsupported job type in MappingJobQueue (MBID Mapping Writer).")
        except Exception as err:
            self.app.logger.info(traceback.format_exc())

        self.app.logger.info("job queue thread finished")
