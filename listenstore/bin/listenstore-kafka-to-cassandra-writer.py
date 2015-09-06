#!/usr/bin/env python
from listenstore.cli import Command


class KafkaToCassandra(Command):
    desc = "Print listens fetched from kafka"

    def received_listen(self, listen):
        self.log("INSERTING: %s" % repr(listen))
        self.listenStore.insert(listen)

    def run(self):
        self.kafkaConsumer.start_listens(self.received_listen)


if __name__ == '__main__':
    KafkaToCassandra().start()
