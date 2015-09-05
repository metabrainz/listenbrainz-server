#!/usr/bin/env python

import config
import json
import logging 
from logging.handlers import RotatingFileHandler
from kafka import KafkaClient, SimpleConsumer
from cassandra.cluster import Cluster

LOG_FILE_MAX_SIZE = 512 * 1024
LOG_FILE_BACKUP_COUNT = 100
try:
    LOG_FILE = config.CASSANDRA_CONSUMER_LOG_FILE
    LOG_FILE_ENABLED = config.CASSANDRA_CONSUMER_LOG_FILE_ENABLED
except AttributeError:
    LOG_FILE = None
    LOG_FILE_ENABLED = False

log = logging.getLogger('cassandra_consumer')

if LOG_FILE_ENABLED:
    file_handler = RotatingFileHandler(LOG_FILE,
                                       maxBytes=LOG_FILE_MAX_SIZE,
                                       backupCount=LOG_FILE_BACKUP_COUNT)
    file_handler.setLevel(logging.INFO)
    log.addHandler(file_handler)

client = KafkaClient(config.KAFKA_CONNECT)

cluster = Cluster()
session = cluster.connect(config.CASSANDRA_CLUSTER)

consumer = SimpleConsumer(client, b"listen-group", b"listens")
for message in consumer:
    data =  message.message.value
    try:
        data = json.loads(data)
    except ValueError:
        log.error("Cannot parse JSON: '%s'" % message)

    uid = data['user_id']
    id_key = data['listened_at']
    id = id_key[0:3]

    session.execute("""INSERT INTO listens (uid, id_key, id, json) VALUES 
                       (%s, %s, %s, %s)""", (uid, id_key, id, data))

