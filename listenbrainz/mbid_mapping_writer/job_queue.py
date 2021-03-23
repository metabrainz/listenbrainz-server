from queue import PriorityQueue
from  concurrent.futures import ThreadPoolExecutor
import threading

from flask import current_app
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_PLAYING_NOW

JOB_ENTRY_NEW_LISTENS = 0
JOB_ENTRY_OLD_LISTENS = 1


class MappingJobQueue(threading.Thread):

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app
        self.queue = PriorityQueue()

    def add_new_listens(self, listens, delivery_tag):
        self.queue.put((JOB_ENTRY_NEW_LISTENS, listens, delivery_tag))

    def run(self):
        with self.app.app_context():
            with concurrent.futures.ThreadPoolExecutor() as executor:


