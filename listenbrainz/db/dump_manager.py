""" This module contains a click group with commands to
create and import postgres data dumps.
"""

# listenbrainz-server - Server for the ListenBrainz project
#
# Copyright (C) 2017 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import click
import listenbrainz.db.dump as db_dump
import logging
import os
import sys

from datetime import datetime
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from listenbrainz import db
from listenbrainz.utils import create_path
from listenbrainz.webserver.influx_connection import init_influx_connection

import listenbrainz.default_config as config
try:
    import listenbrainz.custom_config as config
except ImportError:
    pass

log = logging.getLogger(__name__)

cli = click.Group()

@cli.command()
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int)
def create(location, threads):
    """ Create a ListenBrainz data dump which includes a private dump, a statistics dump
        and a dump of the actual listens from InfluxDB

        Args:
            location (str): path to the directory where the dump should be made
            threads (int): the number of threads to be used while compression
    """
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    ls = init_influx_connection(log,  {
        'REDIS_HOST': config.REDIS_HOST,
        'REDIS_PORT': config.REDIS_PORT,
        'INFLUX_HOST': config.INFLUX_HOST,
        'INFLUX_PORT': config.INFLUX_PORT,
        'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
    })
    time_now = datetime.today()
    dump_path = os.path.join(location, 'listenbrainz-dump-{time}'.format(time=time_now.strftime('%Y%m%d-%H%M%S')))
    create_path(dump_path)
    db_dump.dump_postgres_db(dump_path, time_now, threads)
    ls.dump_listens(dump_path, time_now, threads)


@cli.command()
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
def import_db(location):
    """ Import a ListenBrainz PostgreSQL dump into the PostgreSQL database.

        Note: This method tries to import the private dump first, followed by the statistics
            dump. However, in absence of a private dump, it imports sanitized versions of the
            user table in the statistics dump in order to satisfy foreign key constraints.

        Args:
            location (str): path to the directory which contains the private and the stats dump
    """
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    db_dump.import_postgres_dump(location)


@cli.command()
@click.option('--location', '-l')
@click.option('--threads', '-t', type=int)
def import_listens(location=None, threads=None):
    """ Import a ListenBrainz listen dump into the Influx database.

        Args:
            location (str): path to the listenbrainz listen .tar.xz archive
            threads (int): the number of threads to use while decompressing, defaults to 1
    """

    if not location:
        print('No location given!')
        sys.exit(1)

    ls = init_influx_connection(log,  {
        'REDIS_HOST': config.REDIS_HOST,
        'REDIS_PORT': config.REDIS_PORT,
        'INFLUX_HOST': config.INFLUX_HOST,
        'INFLUX_PORT': config.INFLUX_PORT,
        'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
    })

    try:
        ls.import_listens_dump(location, threads)
    except IOError as e:
        log.error('IOError while trying to import data into Influx: %s', str(e))
        raise
    except InfluxDBClientError as e:
        log.error('Error while sending data to Influx: %s', str(e))
        raise
    except InfluxDBServerError as e:
        log.error('InfluxDB Server Error while importing data: %s', str(e))
        raise
    except Exception as e:
        log.error('Unexpected error while importing data: %s', str(e))
        raise
