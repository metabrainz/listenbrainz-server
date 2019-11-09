#!/usr/bin/env python3

from time import time, sleep
from listenbrainz_spark.request_consumer import request_consumer

def main():
    request_consumer.main("request_consumer-%s" % str(int(time())))


if __name__ == "__main__":
    main()
