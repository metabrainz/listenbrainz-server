#!/usr/bin/env python
import logging
from listenstore.cli import Command


class KafkaToCassandra(Command):
    desc = "Print listens fetched from kafka"

    def __init__(self):
        super(KafkaToCassandra, self).__init__()
        self.log = logging.getLogger(__name__)
        self.inserts = 0

    def received_listen(self, listen):
        self.log.debug("INSERTING: %s" % repr(listen))
        self.listenStore.insert(listen)
        self.inserts += 1
        if self.inserts % 100 == 0:
            self.log.info("inserted from kafka -> cassandra: %d" % self.inserts)

    def run(self):
        self.kafkaConsumer.start_listens(self.received_listen)


if __name__ == '__main__':
    KafkaToCassandra().start()
