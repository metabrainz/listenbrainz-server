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
import re
import shutil
import sys

from datetime import datetime
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from listenbrainz import db
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.utils import create_path
from listenbrainz.webserver.influx_connection import init_influx_connection

from listenbrainz import config as config


NUMBER_OF_DUMPS_TO_KEEP = 2

log = logging.getLogger(__name__)

cli = click.Group()


@cli.command()
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
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
        'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
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
@click.option('--private-archive', '-pr', default=None)
@click.option('--public-archive', '-pu', default=None)
@click.option('--listen-archive', '-l', default=None)
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
def import_dump(private_archive, public_archive, listen_archive, threads):
    """ Import a ListenBrainz dump into the database.

        Note: This method tries to import the private db dump first, followed by the public db
            dump. However, in absence of a private dump, it imports sanitized versions of the
            user table in the public dump in order to satisfy foreign key constraints.

        Then it imports the listen dump.

        Args:
            private_archive (str): the path to the ListenBrainz private dump to be imported
            public_archive (str): the path to the ListenBrainz public dump to be imported
            listen_archive (str): the path to the ListenBrainz listen dump archive to be imported
            threads (int): the number of threads to use during decompression, defaults to 1
    """
    if not private_archive and not public_archive and not listen_archive:
        print('You need to enter a path to the archive(s) to import!')
        sys.exit(1)

    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    db_dump.import_postgres_dump(private_archive, public_archive, threads)

    ls = init_influx_connection(log,  {
        'REDIS_HOST': config.REDIS_HOST,
        'REDIS_PORT': config.REDIS_PORT,
        'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
        'INFLUX_HOST': config.INFLUX_HOST,
        'INFLUX_PORT': config.INFLUX_PORT,
        'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
    })

    try:
        ls.import_listens_dump(listen_archive, threads)
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


@cli.command()
@click.argument('location', type=str)
def delete_old_dumps(location):
    _cleanup_dumps(location)


def _cleanup_dumps(location):
    """ Delete old dumps while keeping the latest two dumps in the specified directory

    Args:
        location (str): the dir which needs to be cleaned up

    Returns:
        (int, int): the number of dumps remaining, the number of dumps deleted
    """
    dump_re = re.compile('listenbrainz-dump-[0-9]*-[0-9]*')
    dumps = [x for x in sorted(os.listdir(location), reverse=True) if dump_re.match(x)]
    if not dumps:
        print('No dumps present in specified directory!')
        return

    keep = dumps[0:NUMBER_OF_DUMPS_TO_KEEP]
    keep_count = 0
    for dump in keep:
        print('Keeping %s...' % dump)
        keep_count += 1

    remove = dumps[NUMBER_OF_DUMPS_TO_KEEP:]
    remove_count = 0
    for dump in remove:
        print('Removing %s...' % dump)
        shutil.rmtree(os.path.join(location, dump))
        remove_count += 1

    print('Deleted %d old exports, kept %d exports!' % (remove_count, keep_count))
    return keep_count, remove_count
