import errno
import os

from datetime import datetime

INFLUX_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
INFLUX_TIME_FORMAT_NANO = "%Y-%m-%dT%H:%M:%S"


def escape(value):
    """ Escapes backslashes, quotes and new lines present in the string value
    """
    return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")


def quote(user_name):
    # we have to always quote the user name to get the measurement name which we pass to
    # influx write_points and replace the new line characters with \n because parse
    # errors are thrown if we don't.
    return "\"{0}\"".format(user_name.replace("\n", "\\n"))


def get_measurement_name(user_name):
    """ Function to return the measurement name that influx has saved for given user name"""

    # Note: there are we have to replace each \ with two backslashes because influxdb-python
    # adds an extra backslash for each backslash in the measurement name itself
    return '"{}"'.format(user_name.replace('\\', '\\\\').replace('\n', '\\\\n'))


def get_escaped_measurement_name(user_name):
    """ Function to return the string which can directly be passed into influx queries for a
        user's measurement
    """

    # Note: influxdb-python first replaces each backslash in the username with two backslashes
    # and because in influx queries, we have to escape each backslash, overall each backslash
    # must be replaced by 4 backslashes. Yes, this is hacky and ugly.
    return '"\\"{}\\""'.format(user_name.replace('\\', '\\\\\\\\').replace('"', '\\"').replace('\n', '\\\\\\\\n'))


def get_influx_query_timestamp(ts):
    """ Influx queries require timestamps in nanoseconds so convert ts into nanoseconds and return a string"""
    return "{}000000000".format(ts)


def convert_to_unix_timestamp(influx_row_time):
    """ Converts time retreived from influxdb into unix timestamp """
    dt = datetime.strptime(influx_row_time, INFLUX_TIME_FORMAT)
    return int(dt.strftime('%s'))


def convert_timestamp_to_influx_row_format(ts):
    return datetime.fromtimestamp(ts).strftime(INFLUX_TIME_FORMAT)


def convert_influx_nano_to_python_time(influx_row_time):
    """ Converts time retreived from influxdb into python floating point time """
    date_bits = influx_row_time.split(".")
    dt = datetime.strptime(date_bits[0], INFLUX_TIME_FORMAT_NANO)
    fractional = int(date_bits[1][:-1])
    return float(dt.strftime('%s')) + (fractional / 100000000.0)


def convert_python_time_to_nano_int(t):
    return int(t * 100000000)


def create_path(path):
    """Creates a directory structure if it doesn't exist yet."""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise Exception("Failed to create directory structure %s. Error: %s" %
                            (path, exception))
