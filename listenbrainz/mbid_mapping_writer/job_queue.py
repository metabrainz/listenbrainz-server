from queue import PriorityQueue, Queue, Empty
from  concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import threading
from time import sleep

from flask import current_app
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_PLAYING_NOW

MAX_THREADS = 4
MAX_QUEUED_JOBS = MAX_THREADS * 2


def lookup_new_listens(listens, delivery_tag):
#    current_app.logger.info("listen lookup!")
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
        with self.app.app_context():
            with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                futures = {}
                while not self.done:

                    completed, uncompleted = wait(futures, return_when=FIRST_COMPLETED)
                    for complete in completed:
                        self.delivery_tag_queue.put(complete.result())
                        del futures[complete]

                    for i in range(MAX_QUEUED_JOBS - len(uncompleted)):
                        try:
                            job = self.queue.get(False)
                        except Empty:
                            break

                        if job[0] > 0:
                            futures[executor.submit(lookup_new_listens, job[1], job[2])] = job[0]
                        else:
                            self.app.logger.info("Unsupported job type in MappingJobQueue (MBID Mapping Writer).")

        self.app.logger.info("job queue thread finished")
