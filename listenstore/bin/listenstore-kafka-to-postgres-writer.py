#!/usr/bin/env python
import logging
from listenstore.cli import Command
from listenstore.listenstore import PostgresListenStore



class KafkaToPostgres(Command):
    desc = "Print listens fetched from kafka"

    def __init__(self):
        super(KafkaToPostgres, self).__init__()
        self.log = logging.getLogger(__name__)

    def run(self):
        self.kafkaConsumer.start_listens(self.listenStore)

    @property
    def listen_store(self):
        self._listenStore = PostgresListenStore(self.config)
        return self._listenStore



if __name__ == '__main__':
    KafkaToPostgres().start()
