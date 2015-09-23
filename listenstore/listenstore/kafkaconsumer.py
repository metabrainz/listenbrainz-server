import ujson
import logging
from kafka import KafkaClient, SimpleConsumer
from .listen import Listen
from time import time, sleep
from cassandra.cluster import NoHostAvailable

KAFKA_READ_TIMEOUT = 5
CASSANDRA_BATCH_SIZE = 1000
REPORT_FREQUENCY = 10000

class KafkaConsumer(object):
    def __init__(self, conf):
        self.log = logging.getLogger(__name__)
        self.client = KafkaClient(conf["kafka_server"])
        self.total_inserts = 0
        self.inserts = 0
        self.listenstore = None


    def start_listens(self, listenstore):
        self.listenstore = listenstore
        return self.start(b"listen-group", b"listens")


    def start(self, group_name, topic_name):
        self.group_name = group_name
        self.topic_name = topic_name
        self.log.info("KafkaConsumer subscribed to %s -> %s" % (group_name, topic_name))
        self.consumer = SimpleConsumer(self.client, self.group_name, self.topic_name)

        t0 = 0
        last_offset = -1
        while True:
            listens = []
            if t0 == 0:
                t0 = time()

            messages = self.consumer.get_messages(count=CASSANDRA_BATCH_SIZE, block=True, timeout=KAFKA_READ_TIMEOUT)
            for message in messages:
                try:
                    data = ujson.loads(message.message.value)
                    listens.append(Listen.from_json(data))
                except ValueError as e:
                    self.log.error("Cannot parse JSON: %s\n'%s'" % (str(e), message.message.value))
                    continue

                last_offset = message.offset

            if listens:
                broken = True
                while broken:
                    try:
                        self.listenstore.insert_batch(listens)
                        broken = False
                    except ValueError as e:
                        self.log.error("Cannot insert listens: %s" % unicode(e))
                        broken = False
                    except NoHostAvailable as e:
                        self.log.error("Cannot insert listens: %s. Sleeping, trying again." % unicode(e))
                        sleep(5)


            self.inserts += len(messages)
            if self.inserts >= REPORT_FREQUENCY:
                t1 = time()
                self.total_inserts += self.inserts
                self.log.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows. last offset: %d" % \
                    (self.inserts, t1 - t0, self.inserts / (t1 - t0), self.total_inserts, last_offset))
                self.inserts = 0
                t0 = 0
