#!/usr/bin/env python3

# This script flushes out the listencounts that are in the 7day retention policy and sums them 
# into the permanent listen count measurement.

import listenbrainz.config as config
from listenbrainz.listenstore import InfluxListenStore

ls = InfluxListenStore({ 'REDIS_HOST' : config.REDIS_HOST,
                         'REDIS_PORT' : config.REDIS_PORT,
                         'INFLUX_HOST': config.INFLUX_HOST,
                         'INFLUX_PORT': config.INFLUX_PORT,
                         'INFLUX_DB_NAME': config.INFLUX_DB_NAME})
ls.update_listen_counts()
