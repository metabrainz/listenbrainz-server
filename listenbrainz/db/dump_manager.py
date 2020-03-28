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
import subprocess
import sys

from brainzutils.mail import send_mail
from datetime import datetime
from flask import current_app, render_template
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from listenbrainz import db
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.utils import create_path
from listenbrainz.webserver import create_app
from listenbrainz.webserver.influx_connection import init_influx_connection


NUMBER_OF_FULL_DUMPS_TO_KEEP = 2
NUMBER_OF_INCREMENTAL_DUMPS_TO_KEEP = 6

cli = click.Group()

def send_dump_creation_notification(dump_name, dump_type):
    if not current_app.config['TESTING']:
        dump_link = 'http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz/{}/{}'.format(dump_type, dump_name)
        send_mail(
            subject="ListenBrainz dump created - {}".format(dump_name),
            text=render_template('emails/data_dump_created_notification.txt', dump_name=dump_name, dump_link=dump_link),
            recipients=['listenbrainz-observability@metabrainz.org'],
            from_name='ListenBrainz',
            from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN']
        )


@cli.command(name="create_full")
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
@click.option('--dump-id', type=int, default=None)
@click.option('--last-dump-id', is_flag=True)
def create_full(location, threads, dump_id, last_dump_id):
    """ Create a ListenBrainz data dump which includes a private dump, a statistics dump
        and a dump of the actual listens from InfluxDB

        Args:
            location (str): path to the directory where the dump should be made
            threads (int): the number of threads to be used while compression
            dump_id (int): the ID of the ListenBrainz data dump
            last_dump_id (bool): flag indicating whether to create a full dump from the last entry in the dump table
    """
    app = create_app()
    with app.app_context():
        from listenbrainz.webserver.influx_connection import _influx as ls
        if last_dump_id:
            all_dumps = db_dump.get_dump_entries()
            if len(all_dumps) == 0:
                current_app.logger.error("Cannot create full dump with last dump's ID, no dump exists!")
                sys.exit(-1)
            dump_id = all_dumps[0]['id']

        if dump_id is None:
            end_time = datetime.now()
            dump_id = db_dump.add_dump_entry(int(end_time.strftime('%s')))
        else:
            dump_entry = db_dump.get_dump_entry(dump_id)
            if dump_entry is None:
                current_app.logger.error("No dump with ID %d found", dump_id)
                sys.exit(-1)
            end_time = dump_entry['created']

        dump_name = 'listenbrainz-dump-{dump_id}-{time}-full'.format(dump_id=dump_id, time=end_time.strftime('%Y%m%d-%H%M%S'))
        dump_path = os.path.join(location, dump_name)
        create_path(dump_path)
        db_dump.dump_postgres_db(dump_path, end_time, threads)
        ls.dump_listens(dump_path, dump_id=dump_id, end_time=end_time, threads=threads, spark_format=False)
        ls.dump_listens(dump_path, dump_id=dump_id, end_time=end_time, threads=threads, spark_format=True)
        try:
            write_hashes(dump_path)
        except IOError as e:
            current_app.logger.error('Unable to create hash files! Error: %s', str(e), exc_info=True)
            return

        # if in production, send an email to interested people for observability
        send_dump_creation_notification(dump_name, 'fullexport')

        current_app.logger.info('Dumps created and hashes written at %s' % dump_path)


@cli.command(name="create_incremental")
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
@click.option('--dump-id', type=int, default=None)
def create_incremental(location, threads, dump_id):
    app = create_app()
    with app.app_context():
        from listenbrainz.webserver.influx_connection import _influx as ls
        if dump_id is None:
            end_time = datetime.now()
            dump_id = db_dump.add_dump_entry(int(end_time.strftime('%s')))
        else:
            dump_entry = db_dump.get_dump_entry(dump_id)
            if dump_entry is None:
                current_app.logger.error("No dump with ID %d found, exiting!", dump_id)
                sys.exit(-1)
            end_time = dump_entry['created']

        prev_dump_entry = db_dump.get_dump_entry(dump_id - 1)
        if prev_dump_entry is None: # incremental dumps must have a previous dump in the series
            current_app.logger.error("Invalid dump ID %d, could not find previous dump", dump_id)
            sys.exit(-1)
        start_time = prev_dump_entry['created']
        current_app.logger.info("Dumping data from %s to %s", start_time, end_time)

        dump_name = 'listenbrainz-dump-{dump_id}-{time}-incremental'.format(dump_id=dump_id, time=end_time.strftime('%Y%m%d-%H%M%S'))
        dump_path = os.path.join(location, dump_name)
        create_path(dump_path)
        ls.dump_listens(dump_path, dump_id=dump_id, start_time=start_time, end_time=end_time, threads=threads, spark_format=False)
        ls.dump_listens(dump_path, dump_id=dump_id, start_time=start_time, end_time=end_time, threads=threads, spark_format=True)
        try:
            write_hashes(dump_path)
        except IOError as e:
            current_app.logger.error('Unable to create hash files! Error: %s', str(e), exc_info=True)
            return

        # if in production, send an email to interested people for observability
        send_dump_creation_notification(dump_name, 'incremental')

        current_app.logger.info('Dumps created and hashes written at %s' % dump_path)


@cli.command()
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
def create_spark_dump(location, threads):
    with create_app().app_context():
        from listenbrainz.webserver.influx_connection import _influx as ls
        time_now = datetime.today()
        dump_path = os.path.join(location, 'listenbrainz-spark-dump-{time}'.format(time=time_now.strftime('%Y%m%d-%H%M%S')))
        create_path(dump_path)
        ls.dump_listens(dump_path, time_now, threads, spark_format=True)
        try:
            write_hashes(dump_path)
        except IOError as e:
            current_app.logger.error('Unable to create hash files! Error: %s', str(e), exc_info=True)
            return
        current_app.logger.info('Dump created and hash written at %s', dump_path)


@cli.command(name="import_dump")
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

    app = create_app()
    with app.app_context():
        db_dump.import_postgres_dump(private_archive, public_archive, threads)

        from listenbrainz.webserver.influx_connection import _influx as ls
        try:
            ls.import_listens_dump(listen_archive, threads)
        except IOError as e:
            current_app.logger.critical('IOError while trying to import data into Influx: %s', str(e), exc_info=True)
            raise
        except InfluxDBClientError as e:
            current_app.logger.critical('Error while sending data to Influx: %s', str(e), exc_info=True)
            raise
        except InfluxDBServerError as e:
            current_app.logger.critical('InfluxDB Server Error while importing data: %s', str(e), exc_info=True)
            raise
        except Exception as e:
            current_app.logger.critical('Unexpected error while importing data: %s', str(e), exc_info=True)
            raise


@cli.command(name="delete_old_dumps")
@click.argument('location', type=str)
def delete_old_dumps(location):
    _cleanup_dumps(location)


def get_dump_id(dump_name):
    return int(dump_name.split('-')[2])


def _cleanup_dumps(location):
    """ Delete old dumps while keeping the latest two dumps in the specified directory

    Args:
        location (str): the dir which needs to be cleaned up

    Returns:
        (int, int): the number of dumps remaining, the number of dumps deleted
    """
    full_dump_re = re.compile('listenbrainz-dump-[0-9]*-[0-9]*-[0-9]*-full')
    dump_files = [x for x in os.listdir(location) if full_dump_re.match(x)]
    full_dumps = [x for x in sorted(dump_files, key=get_dump_id, reverse=True)]
    if not full_dumps:
        print('No full dumps present in specified directory!')
    else:
        remove_dumps(location, full_dumps, NUMBER_OF_FULL_DUMPS_TO_KEEP)

    incremental_dump_re = re.compile('listenbrainz-dump-[0-9]*-[0-9]*-[0-9]*-incremental')
    dump_files = [x for x in os.listdir(location) if incremental_dump_re.match(x)]
    incremental_dumps = [x for x in sorted(dump_files, key=get_dump_id, reverse=True)]
    if not incremental_dumps:
        print('No full dumps present in specified directory!')
    else:
        remove_dumps(location, incremental_dumps, NUMBER_OF_INCREMENTAL_DUMPS_TO_KEEP)


def remove_dumps(location, dumps, remaining_count):
    keep = dumps[0:remaining_count]
    keep_count = 0
    for dump in keep:
        print('Keeping %s...' % dump)
        keep_count += 1

    remove = dumps[remaining_count:]
    remove_count = 0
    for dump in remove:
        print('Removing %s...' % dump)
        shutil.rmtree(os.path.join(location, dump))
        remove_count += 1

    print('Deleted %d old exports, kept %d exports!' % (remove_count, keep_count))
    return keep_count, remove_count


def write_hashes(location):
    """ Create hash files for each file in the given dump location

    Args:
        location (str): the path in which the dump archive files are present
    """
    for file in os.listdir(location):
        try:
            with open(os.path.join(location, '{}.md5'.format(file)), 'w') as f:
                md5sum = subprocess.check_output(['md5sum', os.path.join(location, file)]).decode('utf-8').split()[0]
                f.write(md5sum)
            with open(os.path.join(location, '{}.sha256'.format(file)), 'w') as f:
                sha256sum = subprocess.check_output(['sha256sum', os.path.join(location, file)]).decode('utf-8').split()[0]
                f.write(sha256sum)
        except IOError as e:
            current_app.logger.error('IOError while trying to write hash files for file %s: %s', file, str(e), exc_info=True)
            raise
