import traceback
from queue import Queue, Empty
from time import monotonic, sleep
import threading
from listenbrainz.utils import init_cache
from brainzutils import metrics


UPDATE_INTERVAL = 30


class SpotifyIdsQueue(threading.Thread):
    """ This class coordinates incoming listens and legacy listens, giving
        priority to new and incoming listens. Threads are fired off as needed
        looking up jobs in the background and then this main matcher
        thread can deal with the statstics and reporting"""

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.done = False
        self.app = app
        self.queue = Queue()

        init_cache(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'],
                   namespace=app.config['REDIS_NAMESPACE'])
        metrics.init("listenbrainz")

    def add_spotify_ids(self, ids):
        for spotify_id in ids:
            self.queue.put(spotify_id)

    def terminate(self):
        self.done = True
        self.join()

    def update_metrics(self, stats):
        """ Calculate stats and print status to stdout and report metrics."""
        # metrics.set("listenbrainz-spotify-metadata-cache", )

    def process_spotify_id(self, spotify_id):
        pass

    def run(self):
        """ main thread entry point"""
        stats = {}

        # the main thread loop
        update_time = monotonic() + UPDATE_INTERVAL
        try:
            with self.app.app_context():
                while not self.done:
                    try:
                        spotify_id = self.queue.get(False)
                        self.process_spotify_id(spotify_id)
                    except Empty:
                        sleep(.1)
                        continue

                    if monotonic() > update_time:
                        update_time = monotonic() + UPDATE_INTERVAL
                        self.update_metrics(stats)
        except Exception:
            self.app.logger.info(traceback.format_exc())

        self.app.logger.info("job queue thread finished")
