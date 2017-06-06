# coding=utf-8

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
COUNT_RETENTION_POLICY = "one_week"
COUNT_MEASUREMENT_NAME = "listen_count"
TEMP_COUNT_MEASUREMENT = COUNT_RETENTION_POLICY + "." + COUNT_MEASUREMENT_NAME
TIMELINE_COUNT_MEASUREMENT = COUNT_MEASUREMENT_NAME

influx = InfluxDBClient(host="influx", port=8086, database="listenbrainz")
try:
    results  = influx.query("""SELECT %s
                                    FROM "%s"
                                ORDER BY time""" % (COUNT_MEASUREMENT_NAME, TEMP_COUNT_MEASUREMENT))
except (InfluxDBServerError, InfluxDBClientError) as err:
    print("Cannot query influx: %s" % str(err))
    raise

for result in results.get_points(measurement=TEMP_COUNT_MEASUREMENT):
    print(result['time'], result[COUNT_MEASUREMENT_NAME])
