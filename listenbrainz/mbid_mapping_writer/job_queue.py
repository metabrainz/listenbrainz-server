from queue import PriorityQueue, Queue
from  concurrent.futures import ThreadPoolExecutor
import threading

from flask import current_app
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_PLAYING_NOW

MAX_THREADS = 4
MAX_QUEUED_JOBS = MAX_THREADS * 2
JOB_ENTRY_NEW_LISTENS = 0
JOB_ENTRY_OLD_LISTENS = 1


def lookup_new_listens(listens, delivery_tag):
    return delivery_tag


class MappingJobQueue(threading.Thread):

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.done = False
        self.app = app
        self.queue = PriorityQueue()
        self.delivery_tag_queue = Queue()

    def get_completed_delivery_tags(self):

        tags = []
        while True:
            tag = self.self.delivery_tag_queue.get(False)
            if not tag:
                break
            tags.append(tag)

        return tags

    def add_new_listens(self, listens, delivery_tag):
        self.queue.put((JOB_ENTRY_NEW_LISTENS, listens, delivery_tag))

    def terminate(self):
        self.done = True
        self.join()

    def run(self):
        with self.app.app_context():
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                while not self.done:
                    completed, uncompleted = concurrent.futures.wait(
                        futures, timeout=1.0, return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    for complete in completed:
                        job = futures.pop(complete)
                        self.self.delivery_tag_queue.put(job.result())

                    for i in range(MAX_QUEUED_JOBS - len(uncompleted)):
                        job = self.queue.get(False)
                        if not job:
                            break

                        if job[0] == JOB_ENTRY_NEW_LISTENS:
                            executor.submit(lookup_new_listens, job[1], job[2])
                        else:
                            self.app.error("Unsupported job type in MappingJobQueue (MBID Mapping Writer).")
