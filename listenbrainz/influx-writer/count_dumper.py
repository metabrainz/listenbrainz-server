#!/usr/bin/env python3


import sys
import os
import pika
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import listenbrainz.config as config
from listenbrainz.listenstore import InfluxListenStore
from listenbrainz.utils import escape, get_measurement_name, get_escaped_measurement_name, \
                               get_influx_query_timestamp, convert_to_unix_timestamp, \
                               convert_timestamp_to_influx_row_format

COUNT_RETENTION_POLICY = "one_week"
COUNT_MEASUREMENT_NAME = "listen_count"
TEMP_COUNT_MEASUREMENT = COUNT_RETENTION_POLICY + "." + COUNT_MEASUREMENT_NAME
TIMELINE_COUNT_MEASUREMENT = COUNT_MEASUREMENT_NAME

influx = InfluxDBClient(host=config.INFLUX_HOST, port=config.INFLUX_PORT, database=config.INFLUX_DB_NAME)
try:
    result = influx.query("""SELECT "%s" as count
                               FROM "%s" """ % (COUNT_MEASUREMENT_NAME, TEMP_COUNT_MEASUREMENT))
except (InfluxDBServerError, InfluxDBClientError) as err:
    self.log.error("Cannot query influx: %s" % str(err))
    raise

total = 0
try:
    for data in result.get_points(measurement = TEMP_COUNT_MEASUREMENT):
        print("%s - %d" % (data['time'], int(data['count'])))
        total += int(data['count'])
except StopIteration:
    pass

print("total count entries: %d" % total)
