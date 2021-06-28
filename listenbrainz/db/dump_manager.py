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
from datetime import datetime, timedelta
from ftplib import FTP
import listenbrainz.db.dump as db_dump
import logging
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

import psycopg2
import ujson
from flask import current_app, render_template
from brainzutils.mail import send_mail
from listenbrainz import db
from listenbrainz.listen import convert_dump_row_to_spark_row
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.utils import create_path
from listenbrainz.webserver import create_app
from listenbrainz.webserver.timescale_connection import init_timescale_connection
from listenbrainz.db.dump import check_ftp_dump_ages


NUMBER_OF_FULL_DUMPS_TO_KEEP = 2
NUMBER_OF_INCREMENTAL_DUMPS_TO_KEEP = 30
NUMBER_OF_FEEDBACK_DUMPS_TO_KEEP = 2

cli = click.Group()


def send_dump_creation_notification(dump_name, dump_type):
    if not current_app.config['TESTING']:
        dump_link = 'http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz/{}/{}'.format(
            dump_type, dump_name)
        send_mail(
            subject="ListenBrainz {} dump created - {}".format(
                dump_type, dump_name),
            text=render_template('emails/data_dump_created_notification.txt',
                                 dump_name=dump_name, dump_link=dump_link),
            recipients=['listenbrainz-observability@metabrainz.org'],
            from_name='ListenBrainz',
            from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN']
        )


@cli.command(name="create_full")
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
@click.option('--dump-id', type=int, default=None)
def create_full(location, threads, dump_id):
    """ Create a ListenBrainz data dump which includes a private dump, a statistics dump
        and a dump of the actual listens from the listenstore

        Args:
            location (str): path to the directory where the dump should be made
            threads (int): the number of threads to be used while compression
            dump_id (int): the ID of the ListenBrainz data dump
    """
    app = create_app()
    with app.app_context():
        from listenbrainz.webserver.timescale_connection import _ts as ls
        if dump_id is None:
            end_time = datetime.now()
            dump_id = db_dump.add_dump_entry(int(end_time.strftime('%s')))
        else:
            dump_entry = db_dump.get_dump_entry(dump_id)
            if dump_entry is None:
                current_app.logger.error("No dump with ID %d found", dump_id)
                sys.exit(-1)
            end_time = dump_entry['created']

        ts = end_time.strftime('%Y%m%d-%H%M%S')
        dump_name = 'listenbrainz-dump-{dump_id}-{time}-full'.format(
            dump_id=dump_id, time=ts)
        dump_path = os.path.join(location, dump_name)
        create_path(dump_path)
        db_dump.dump_postgres_db(dump_path, end_time, threads)

        listens_dump_file = ls.dump_listens(
            dump_path, dump_id=dump_id, end_time=end_time, threads=threads)
        spark_dump_file = 'listenbrainz-listens-dump-{dump_id}-{time}-spark-full.tar.xz'.format(dump_id=dump_id,
                                                                                                time=ts)
        spark_dump_path = os.path.join(location, dump_path, spark_dump_file)
        transmogrify_dump_file_to_spark_import_format(
            listens_dump_file, spark_dump_path, threads)

        try:
            write_hashes(dump_path)
        except IOError as e:
            current_app.logger.error(
                'Unable to create hash files! Error: %s', str(e), exc_info=True)
            sys.exit(-1)

        try:
            if not sanity_check_dumps(dump_path, 12):
                return sys.exit(-1)
        except OSError as e:
            sys.exit(-1)

        # if in production, send an email to interested people for observability
        send_dump_creation_notification(dump_name, 'fullexport')

        current_app.logger.info(
            'Dumps created and hashes written at %s' % dump_path)

        # Write the DUMP_ID file so that the FTP sync scripts can be more robust
        with open(os.path.join(dump_path, "DUMP_ID.txt"), "w") as f:
            f.write("%s %s full\n" % (ts, dump_id))

        sys.exit(0)


@cli.command(name="create_incremental")
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
@click.option('--dump-id', type=int, default=None)
def create_incremental(location, threads, dump_id):
    app = create_app()
    with app.app_context():
        from listenbrainz.webserver.timescale_connection import _ts as ls
        if dump_id is None:
            end_time = datetime.now()
            dump_id = db_dump.add_dump_entry(int(end_time.strftime('%s')))
        else:
            dump_entry = db_dump.get_dump_entry(dump_id)
            if dump_entry is None:
                current_app.logger.error(
                    "No dump with ID %d found, exiting!", dump_id)
                sys.exit(-1)
            end_time = dump_entry['created']

        prev_dump_entry = db_dump.get_dump_entry(dump_id - 1)
        if prev_dump_entry is None:  # incremental dumps must have a previous dump in the series
            current_app.logger.error(
                "Invalid dump ID %d, could not find previous dump", dump_id)
            sys.exit(-1)
        start_time = prev_dump_entry['created']
        current_app.logger.info(
            "Dumping data from %s to %s", start_time, end_time)

        dump_name = 'listenbrainz-dump-{dump_id}-{time}-incremental'.format(
            dump_id=dump_id, time=end_time.strftime('%Y%m%d-%H%M%S'))
        dump_path = os.path.join(location, dump_name)
        create_path(dump_path)
        listens_dump_file = ls.dump_listens(
            dump_path, dump_id=dump_id, start_time=start_time, end_time=end_time, threads=threads)
        spark_dump_file = 'listenbrainz-listens-dump-{dump_id}-{time}-spark-incremental.tar.xz'.format(dump_id=dump_id,
                                                                                                       time=end_time.strftime('%Y%m%d-%H%M%S'))
        spark_dump_path = os.path.join(location, dump_path, spark_dump_file)
        transmogrify_dump_file_to_spark_import_format(
            listens_dump_file, spark_dump_path, threads)
        try:
            write_hashes(dump_path)
        except IOError as e:
            current_app.logger.error(
                'Unable to create hash files! Error: %s', str(e), exc_info=True)
            sys.exit(-1)

        try:
            if not sanity_check_dumps(dump_path, 6):
                return sys.exit(-1)
        except OSError as e:
            sys.exit(-1)

        # if in production, send an email to interested people for observability
        send_dump_creation_notification(dump_name, 'incremental')

        # Write the DUMP_ID file so that the FTP sync scripts can be more robust
        with open(os.path.join(dump_path, "DUMP_ID.txt"), "w") as f:
            f.write("%s %s incremental\n" %
                    (end_time.strftime('%Y%m%d-%H%M%S'), dump_id))

        current_app.logger.info(
            'Dumps created and hashes written at %s' % dump_path)
        sys.exit(0)


@cli.command(name="create_feedback")
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
def create_feedback(location, threads):
    """ Create a spark formatted dump of user/recommendation feedback data.

        Args:
            location (str): path to the directory where the dump should be made
            threads (int): the number of threads to be used while compression
    """
    app = create_app()
    with app.app_context():

        end_time = datetime.now()
        ts = end_time.strftime('%Y%m%d-%H%M%S')
        dump_name = 'listenbrainz-feedback-{time}-full'.format(time=ts)
        dump_path = os.path.join(location, dump_name)
        create_path(dump_path)
        db_dump.dump_feedback_for_spark(dump_path, end_time, threads)

        try:
            write_hashes(dump_path)
        except IOError as e:
            current_app.logger.error(
                'Unable to create hash files! Error: %s', str(e), exc_info=True)
            sys.exit(-1)

        try:
            if not sanity_check_dumps(dump_path, 3):
                sys.exit(-1)
        except OSError as e:
            sys.exit(-1)

        # if in production, send an email to interested people for observability
        send_dump_creation_notification(dump_name, 'feedback')

        # Write the DUMP_ID file so that the FTP sync scripts can be more robust
        with open(os.path.join(dump_path, "DUMP_ID.txt"), "w") as f:
            f.write("%s 0 feedback\n" % (end_time.strftime('%Y%m%d-%H%M%S')))

        current_app.logger.info(
            'Feedback dump created and hashes written at %s' % dump_path)

        sys.exit(0)


@cli.command(name="import_dump")
@click.option('--private-archive', '-pr', default=None, required=True)
@click.option('--public-archive', '-pu', default=None, required=True)
@click.option('--listen-archive', '-l', default=None, required=True)
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
    app = create_app()
    with app.app_context():
        db_dump.import_postgres_dump(private_archive, public_archive, threads)

        from listenbrainz.webserver.timescale_connection import _ts as ls
        try:
            ls.import_listens_dump(listen_archive, threads)
        except psycopg2.OperationalError as e:
            current_app.logger.critical(
                'OperationalError while trying to import data: %s', str(e), exc_info=True)
            raise
        except IOError as e:
            current_app.logger.critical(
                'IOError while trying to import data: %s', str(e), exc_info=True)
            raise
        except Exception as e:
            current_app.logger.critical(
                'Unexpected error while importing data: %s', str(e), exc_info=True)
            raise

    sys.exit(0)


@cli.command(name="delete_old_dumps")
@click.argument('location', type=str)
def delete_old_dumps(location):
    _cleanup_dumps(location)
    sys.exit(0)


@cli.command(name="check_dump_ages")
def check_dump_ages():
    """Check to make sure that data dumps are sufficiently fresh. Send mail if they are not."""
    check_ftp_dump_ages()
    sys.exit(0)


def get_dump_id(dump_name):
    return int(dump_name.split('-')[2])


def get_dump_ts(dump_name):
    return dump_name.split('-')[2] + dump_name.split('-')[3]


def _cleanup_dumps(location):
    """ Delete old dumps while keeping the latest two dumps in the specified directory

    Args:
        location (str): the dir which needs to be cleaned up

    Returns:
        (int, int): the number of dumps remaining, the number of dumps deleted
    """

    # Clean up full dumps
    full_dump_re = re.compile('listenbrainz-dump-[0-9]*-[0-9]*-[0-9]*-full')
    dump_files = [x for x in os.listdir(location) if full_dump_re.match(x)]
    full_dumps = [x for x in sorted(dump_files, key=get_dump_id, reverse=True)]
    if not full_dumps:
        print('No full dumps present in specified directory!')
    else:
        remove_dumps(location, full_dumps, NUMBER_OF_FULL_DUMPS_TO_KEEP)

    # Clean up incremental dumps
    incremental_dump_re = re.compile(
        'listenbrainz-dump-[0-9]*-[0-9]*-[0-9]*-incremental')
    dump_files = [x for x in os.listdir(
        location) if incremental_dump_re.match(x)]
    incremental_dumps = [x for x in sorted(
        dump_files, key=get_dump_id, reverse=True)]
    if not incremental_dumps:
        print('No incremental dumps present in specified directory!')
    else:
        remove_dumps(location, incremental_dumps,
                     NUMBER_OF_INCREMENTAL_DUMPS_TO_KEEP)

    # Clean up spark / feedback dumps
    spark_dump_re = re.compile(
        'listenbrainz-feedback-[0-9]*-[0-9]*-full')
    dump_files = [x for x in os.listdir(
        location) if spark_dump_re.match(x)]
    spark_dumps = [x for x in sorted(
        dump_files, key=get_dump_ts, reverse=True)]
    if not spark_dumps:
        print('No spark feedback dumps present in specified directory!')
    else:
        remove_dumps(location, spark_dumps,
                     NUMBER_OF_FEEDBACK_DUMPS_TO_KEEP)


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

    print('Deleted %d old exports, kept %d exports!' %
          (remove_count, keep_count))
    return keep_count, remove_count


def write_hashes(location):
    """ Create hash files for each file in the given dump location

    Args:
        location (str): the path in which the dump archive files are present
    """
    for file in os.listdir(location):
        try:
            with open(os.path.join(location, '{}.md5'.format(file)), 'w') as f:
                md5sum = subprocess.check_output(
                    ['md5sum', os.path.join(location, file)]).decode('utf-8').split()[0]
                f.write(md5sum)
            with open(os.path.join(location, '{}.sha256'.format(file)), 'w') as f:
                sha256sum = subprocess.check_output(
                    ['sha256sum', os.path.join(location, file)]).decode('utf-8').split()[0]
                f.write(sha256sum)
        except OSError as e:
            current_app.logger.error(
                'IOError while trying to write hash files for file %s: %s', file, str(e), exc_info=True)
            raise


def sanity_check_dumps(location, expected_count):
    """ Sanity check the generated dumps to ensure that none are empty
        and make sure that the right number of dump files exist.

    Args:
        location (str): the path in which the dump archive files are present
        expected_count (int): the number of files that are expected to be present
    Return:
        boolean: true if the dump passes the sanity check
    """

    count = 0
    for file in os.listdir(location):
        try:
            dump_file = os.path.join(location, file)
            if os.path.getsize(dump_file) == 0:
                print("Dump file %s is empty!" % dump_file)
                return False
            count += 1
        except OSError as e:
            return False

    if expected_count == count:
        return True

    print("Expected %d dump files, found %d. Aborting." %
          (expected_count, count))
    return False


def transmogrify_dump_file_to_spark_import_format(in_file, out_file, threads):
    """ Decompress and convert an LB dump,  ready for spark.

    Args:
        in_file: The tar.xz dump file to import
        out_file: The spark dump file the dump should be mogrified to.
        threads: The number of threads to use to compress the spark dump
    """
    try:
        with tarfile.open(in_file, "r:xz") as tarf:  # yep, going with that one again!
            with open(out_file, 'w') as archive:
                pxz_command = ['pxz', '--compress',
                               '-T{threads}'.format(threads=threads)]
                pxz = subprocess.Popen(
                    pxz_command, stdin=subprocess.PIPE, stdout=archive)

                with tarfile.open(fileobj=pxz.stdin, mode='w|') as out_tar:
                    for member in tarf:
                        if member.name.endswith(".listens"):
                            filename = member.name.replace(".listens", ".json")
                            filename = filename.replace("-full", "-spark-full")
                            print("mogrify: ", filename)
                            tmp_file = tempfile.mkstemp()
                            with os.fdopen(tmp_file[0], "w") as out_f:
                                with tarf.extractfile(member) as f:
                                    while True:
                                        line = f.readline()
                                        if not line:
                                            break

                                        listen = ujson.loads(line)
                                        out_f.write(ujson.dumps(
                                            convert_dump_row_to_spark_row(listen)) + "\n")
                            out_tar.add(tmp_file[1], arcname=filename)
                            os.unlink(tmp_file[1])

                pxz.stdin.close()

            pxz.wait()

    except IOError as e:
        current_app.logger.error('IOError while trying to mogrify spark dump file for file %s -> %s: %s',
                                 in_file, out_file, str(e), exc_info=True)
        raise
