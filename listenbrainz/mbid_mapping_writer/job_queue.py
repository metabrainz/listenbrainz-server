from queue import PriorityQueue, Queue, Empty
from  concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import threading
import traceback
from time import sleep

from flask import current_app
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_PLAYING_NOW
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery

MAX_THREADS = 4
MAX_QUEUED_JOBS = MAX_THREADS * 2


def lookup_new_listens(app, listens, delivery_tag):
    app.logger.info("listen lookup!")
    q = MBIDMappingQuery()
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
        self.app.logger.info("delivery tag %s" % str(delivery_tag))
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
                                self.app.logger.error("\n".join(traceback.format_tb(exc.__traceback__)))
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
