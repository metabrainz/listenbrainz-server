#!/usr/bin/env python


import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
from influxdb import InfluxDBClient
import config

try:
    i = InfluxDBClient(host=config.INFLUX_HOST, port=config.INFLUX_PORT, database=config.INFLUX_TEST_DB)
    i.create_database(config.INFLUX_TEST_DB)
except Exception as e:
    print("Creating influx DB failed: ", e)
