#!/usr/bin/env python
from __future__ import print_function
import sys
import os
from influxdb import InfluxDBClient

def create_influx_db(host, port, db_name):
    try:
        i = InfluxDBClient(host=host, port=port, database=db_name)
        i.create_database(db_name)
        print("Influx DB created!")
    except Exception as e:
        print("Creating influx DB failed: ", e)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: {} <influx_host> <influx_port> <influx_db_name>".format(sys.argv[0]))
        sys.exit(-1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    db_name = sys.argv[3]
    create_influx_db(host, port, db_name)
