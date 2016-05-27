#!/usr/bin/env python
import logging
from listenstore.cli import Command
from listenstore.listenstore import CassandraListenStore



class KafkaToCassandra(Command):
    desc = "Print listens fetched from kafka"

    def __init__(self):
        super(KafkaToCassandra, self).__init__()
        self.log = logging.getLogger(__name__)

    def run(self):
        self.kafka_consumer.start_listens(self.listen_store)

    @property
    def listen_store(self):
        self._listenStore = CassandraListenStore(self.config)
        return self._listenStore



if __name__ == '__main__':
    KafkaToCassandra().start()
