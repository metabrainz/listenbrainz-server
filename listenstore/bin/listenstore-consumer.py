#!/usr/bin/env python
from listenstore.cli import Command
from listenstore.kafkaconsumer import KafkaConsumer


class KafkaPrinter(Command):
    desc = "Print listens fetched from kafka"

    def received_listen(self, listen):
        print repr(listen)

    def run(self):
        self.log.info("KafkaPrinter starting..")
        self.kafkaConsumer = KafkaConsumer(self.config)
        self.kafkaConsumer.start_listens(self.received_listen)


if __name__ == '__main__':
    KafkaPrinter().start()
