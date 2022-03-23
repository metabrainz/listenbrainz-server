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
import listenbrainz.db.dump as db_dump
import os
import re
import shutil
import subprocess
import sys

import psycopg2
from flask import current_app, render_template
from brainzutils.mail import send_mail
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.db.year_in_music import insert_playlists
from listenbrainz.listenstore.dump_listenstore import DumpListenStore
from listenbrainz.utils import create_path
from listenbrainz.webserver import create_app
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
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'),
              help="path to the directory where the dump should be made")
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT,
              help="the number of threads to be used while compression")
@click.option('--dump-id', type=int, default=None,
              help="the ID of the ListenBrainz data dump")
@click.option('--listen/--no-listen', 'do_listen_dump', default=True)
@click.option('--spark/--no-spark', 'do_spark_dump', type=bool, default=True)
@click.option('--db/--no-db', 'do_db_dump', type=bool, default=True)
@click.option('--timescale/--no-timescale', 'do_timescale_dump', type=bool, default=True)
def create_full(location, threads, dump_id, do_listen_dump: bool, do_spark_dump: bool,
                do_db_dump: bool, do_timescale_dump: bool):
    """ Create a ListenBrainz data dump which includes a private dump, a statistics dump
        and a dump of the actual listens from the listenstore.

        Args:
            location (str): path to the directory where the dump should be made
            threads (int): the number of threads to be used while compression
            dump_id (int): the ID of the ListenBrainz data dump
            do_listen_dump: If True, make a listens dump
            do_spark_dump: If True, make a spark listens dump
            do_db_dump: If True, make a public/private postgres dump
            do_timescale_dump: If True, make a public/private timescale dump
    """
    app = create_app()
    with app.app_context():
        ls = DumpListenStore(app)
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

        expected_num_dumps = 0
        if do_db_dump:
            db_dump.dump_postgres_db(dump_path, end_time, threads)
            expected_num_dumps += 2
        if do_timescale_dump:
            db_dump.dump_timescale_db(dump_path, end_time, threads)
            expected_num_dumps += 2
        if do_listen_dump:
            ls.dump_listens(dump_path, dump_id=dump_id, end_time=end_time, threads=threads)
            expected_num_dumps += 1
        if do_spark_dump:
            ls.dump_listens_for_spark(dump_path, dump_id=dump_id, dump_type="full", end_time=end_time)
            expected_num_dumps += 1

        try:
            write_hashes(dump_path)
        except IOError as e:
            current_app.logger.error(
                'Unable to create hash files! Error: %s', str(e), exc_info=True)
            sys.exit(-1)

        try:
            # 6 types of dumps, archive, md5, sha256 for each
            expected_num_dump_files = expected_num_dumps * 3
            if not sanity_check_dumps(dump_path, expected_num_dump_files):
                return sys.exit(-1)
        except OSError:
            sys.exit(-1)

        current_app.logger.info(
            'Dumps created and hashes written at %s' % dump_path)

        # Write the DUMP_ID file so that the FTP sync scripts can be more robust
        with open(os.path.join(dump_path, "DUMP_ID.txt"), "w") as f:
            f.write("%s %s full\n" % (ts, dump_id))

        # if in production, send an email to interested people for observability
        send_dump_creation_notification(dump_name, 'fullexport')

        sys.exit(0)


@cli.command(name="create_incremental")
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'))
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT)
@click.option('--dump-id', type=int, default=None)
def create_incremental(location, threads, dump_id):
    app = create_app()
    with app.app_context():
        ls = DumpListenStore(app)
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

        ls.dump_listens(dump_path, dump_id=dump_id, start_time=start_time, end_time=end_time, threads=threads)
        ls.dump_listens_for_spark(dump_path, dump_id=dump_id, dump_type="incremental",
                                  start_time=start_time, end_time=end_time)

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
@click.option('--location', '-l', default=os.path.join(os.getcwd(), 'listenbrainz-export'),
              help="path to the directory where the dump should be made")
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT,
              help="the number of threads to be used while compression")
def create_feedback(location, threads):
    """ Create a spark formatted dump of user/recommendation feedback data."""
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
@click.option('--private-archive', '-pr', default=None, required=False,
              help="the path to the ListenBrainz private dump to be imported")
@click.option('--private-timescale-archive', default=None, required=False,
              help="the path to the ListenBrainz private timescale dump to be imported")
@click.option('--public-archive', '-pu', default=None, required=False,
              help="the path to the ListenBrainz public dump to be imported")
@click.option('--public-timescale-archive', default=None, required=False,
              help="the path to the ListenBrainz public timescale dump to be imported")
@click.option('--listen-archive', '-l', default=None, required=False,
              help="the path to the ListenBrainz listen dump archive to be imported")
@click.option('--threads', '-t', type=int, default=DUMP_DEFAULT_THREAD_COUNT,
              help="the number of threads to use during decompression, defaults to 1")
def import_dump(private_archive, private_timescale_archive,
                public_archive, public_timescale_archive, listen_archive, threads):
    """ Import a ListenBrainz dump into the database.

    Args:
        private_archive (str): the path to the ListenBrainz private dump to be imported
        private_timescale_archive (str): the path to the ListenBrainz private timescale dump to be imported
        public_archive (str): the path to the ListenBrainz public dump to be imported
        public_timescale_archive (str): the path to the ListenBrainz public timescale dump to be imported
        listen_archive (str): the path to the ListenBrainz listen dump archive to be imported
        threads (int): the number of threads to use during decompression, defaults to 1

    .. note::
        This method tries to import the private db dump first, followed by the public db
        dump. However, in absence of a private dump, it imports sanitized versions of the user
        table in the public dump in order to satisfy foreign key constraints. Then it imports
        the listen dump.
    """
    app = create_app()
    with app.app_context():
        db_dump.import_postgres_dump(private_archive, private_timescale_archive,
                                     public_archive, public_timescale_archive,
                                     threads)
        if listen_archive:
            from listenbrainz.webserver.timescale_connection import _ts as ls
            ls.import_listens_dump(listen_archive, threads)

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


@cli.command(name="create_parquet")
def create_test_parquet_files():
    app = create_app()
    with app.app_context():
        ls = DumpListenStore(app)
        start = datetime.now() - timedelta(days=30)
        ls.dump_listens_for_spark("/tmp", 1000, "full", start)
        sys.exit(-2)


@cli.command(name="import_yim_playlists")
@click.argument('patch-slug', type=str)
@click.argument('dump-file', type=str)
def import_yim_playlists(patch_slug, dump_file):
    """ Import playlist excerpts into the YIM data table from a dump file.

    .. note::
        First copy the dump to inside the container from which the script is to be run.

    Args:
        patch_slug (str): The slug of the troi patch that generated these playlists.
        dump_file (str): The dump file to import. For each user, it should contain
        three lines: user_name, playlist_mbid, JSPF data.
    """
    app = create_app()
    with app.app_context():
        insert_playlists(patch_slug, dump_file)


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
