#!/usr/bin/env python

import config
import json
import logging 
from logging.handlers import RotatingFileHandler
from kafka import KafkaClient, SimpleConsumer
from cassandra.cluster import Cluster
from cassandra import InvalidRequest

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

log.info("your mom")

consumer = SimpleConsumer(client, b"listen-group", b"listens")
for message in consumer:
    json_data =  message.message.value
    try:
        data = json.loads(json_data)
    except ValueError:
        log.error("Cannot parse JSON: '%s'" % message)

    uid = data['user_id']
    id = data['listened_at']
    idkey = int(("%d" % id)[0:3])

#    try:
    session.execute("""INSERT INTO listens (uid, idkey, id, json) VALUES 
                           (%s, %s, %s, %s)""", (uid, idkey, id, json_data))
#    except InvalidRequest as e:
#        log.error("Invalid cassandra insert: ")
