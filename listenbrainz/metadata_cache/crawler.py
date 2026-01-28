import traceback
from queue import Empty
from time import monotonic, sleep
import threading

import sentry_sdk
from brainzutils import metrics

from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.metadata_cache.unique_queue import UniqueQueue, JobItem

UPDATE_INTERVAL = 60  # in seconds
BATCH_SIZE = 10  # number of album ids to process at a time


class Crawler(threading.Thread):

    def __init__(self, app, handler: BaseHandler):
        super().__init__()
        self.done = False
        self.app = app
        self.handler = handler
        self.queue = UniqueQueue()

    def put(self, item: JobItem):
        self.queue.put(item, block=False)

    def terminate(self):
        self.done = True
        self.join()

    def update_metrics(self):
        pending_count = self.queue.size()
        self.app.logger.info("Pending IDs in Queue: %d", pending_count)
        self.app.logger.info("Metrics: %s", self.handler.metrics)
        metrics.set(self.handler.name, pending_count=pending_count, **self.handler.metrics)

    def run(self):
        """ main thread entry point"""
        update_time = monotonic() + UPDATE_INTERVAL
        with self.app.app_context():
            while not self.done:
                if monotonic() > update_time:
                    update_time = monotonic() + UPDATE_INTERVAL
                    self.update_metrics()

                item_ids = []

                try:
                    for _ in range(BATCH_SIZE):
                        item = self.queue.get(block=False)
                        item_ids.append(item.item_id)
                except Empty:
                    if len(item_ids) == 0:
                        sleep(5)
                        continue

                try:
                    items = self.handler.process(item_ids)
                    for item in items:
                        self.put(item)
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    self.app.logger.info(traceback.format_exc())

            self.app.logger.info("job queue thread finished")
