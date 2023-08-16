from dataclasses import dataclass
from queue import PriorityQueue
from threading import Lock


@dataclass(order=True, eq=True, frozen=True)
class JobItem:
    priority: int
    item_id: str


class UniqueQueue:
    def __init__(self):
        self.queue = PriorityQueue()
        self.set = set()
        self.lock = Lock()

    def put(self, d, block=True, timeout=None):
        with self.lock:
            if d not in self.set:
                self.queue.put(d, block, timeout)
                self.set.add(d)
                return True
            return False

    def get(self, block=True, timeout=None):
        with self.lock:
            d = self.queue.get(block, timeout)
            self.set.remove(d)
            return d

    def size(self):
        return self.queue.qsize()

    def empty(self):
        return self.queue.empty()
