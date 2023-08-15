from dataclasses import dataclass
from queue import PriorityQueue


@dataclass(order=True, eq=True, frozen=True)
class JobItem:
    priority: int
    item_id: str


class UniqueQueue:
    def __init__(self):
        self.queue = PriorityQueue()
        self.set = set()

    def put(self, d):
        if d not in self.set:
            self.queue.put(d)
            self.set.add(d)
            return True
        return False

    def get(self):
        d = self.queue.get()
        self.set.remove(d)
        return d

    def size(self):
        return self.queue.qsize()

    def empty(self):
        return self.queue.empty()
