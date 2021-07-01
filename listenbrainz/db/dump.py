""" This module contains data dump creation and import functions.

Read more about the data dumps in our documentation here:
https://listenbrainz.readthedocs.io/en/production/dev/listenbrainz-dumps.html
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


import logging
import os
import shutil
from ftplib import FTP

import sqlalchemy
import subprocess
import sys
import tarfile
import tempfile
import time
import ujson

from datetime import datetime, timedelta

from brainzutils.mail import send_mail
from flask import current_app, render_template
from listenbrainz import DUMP_LICENSE_FILE_PATH
import listenbrainz.db as db
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.utils import create_path, log_ioerrors

from listenbrainz import config
from listenbrainz.webserver import create_app

MAIN_FTP_SERVER_URL = "ftp.eu.metabrainz.org"
FULLEXPORT_MAX_AGE = 17  # days
INCREMENTAL_MAX_AGE = 26  # hours

# this dict contains the tables dumped in public dump as keys
# and a tuple of columns that should be dumped as values
PUBLIC_TABLES = {
    '"user"': (
        'id',
        'created',
        'musicbrainz_id',
        'musicbrainz_row_id',
        # the following are dummy values for columns that we do not want to
        # dump in the public dump
        '\'\'',  # auth token
        'to_timestamp(0)',  # last_login
        'to_timestamp(0)',  # latest_import
    ),
    'statistics.user': (
        'user_id',
        'artist',
        'release',
        'recording',
        'last_updated',
    ),
    'statistics.artist': (
        'id',
        'msid',
        'name',
        'release',
        'recording',
        'listener',
        'listen_count',
        'last_updated',
    ),
    'statistics.release': (
        'id',
        'msid',
        'name',
        'recording',
        'listener',
        'listen_count',
        'last_updated',
    ),
    'statistics.recording': (
        'id',
        'msid',
        'name',
        'listener',
        'listen_count',
        'last_updated',
    ),
    'recording_feedback': (
        'id',
        'user_id',
        'recording_msid',
        'score',
        'created'
    ),
}

# this dict contains the tables dumped in the private dump as keys
# and a tuple of columns that should be dumped as values
PRIVATE_TABLES = {
    '"user"': (
        'id',
        'created',
        'musicbrainz_id',
        'auth_token',
        'last_login',
        'latest_import',
        'musicbrainz_row_id',
        'gdpr_agreed',
        'email',
    ),
    'api_compat.token': (
        'id',
        'user_id',
        'token',
        'api_key',
        'ts',
    ),
    'api_compat.session': (
        'id',
        'user_id',
        'sid',
        'api_key',
        'ts',
    ),
}


def dump_postgres_db(location, dump_time=datetime.today(), threads=None):
    """ Create postgres database dump in the specified location

        Arguments:
            location: Directory where the final dump will be stored
            dump_time: datetime object representing when the dump was started
            threads: Maximal number of threads to run during compression

        Returns:
            a tuple: (path to private dump, path to public dump)
    """

    current_app.logger.info('Beginning dump of PostgreSQL database...')
    current_app.logger.info('dump path: %s', location)

    current_app.logger.info('Creating dump of private data...')
    try:
        private_dump = create_private_dump(location, dump_time, threads)
    except IOError as e:
        current_app.logger.critical(
            'IOError while creating private dump: %s', str(e), exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return
    except Exception as e:
        current_app.logger.critical(
            'Unable to create private db dump due to error %s', str(e), exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return
    current_app.logger.info(
        'Dump of private data created at %s!', private_dump)

    current_app.logger.info('Creating dump of public data...')
    try:
        public_dump = create_public_dump(location, dump_time, threads)
    except IOError as e:
        current_app.logger.critical(
            'IOError while creating public dump: %s', str(e), exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return
    except Exception as e:
        current_app.logger.critical(
            'Unable to create public dump due to error %s', str(e), exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return

    current_app.logger.info('Dump of public data created at %s!', public_dump)

    current_app.logger.info(
        'ListenBrainz PostgreSQL data dump created at %s!', location)
    return private_dump, public_dump


def dump_feedback_for_spark(location, dump_time=datetime.today(), threads=None):
    """ Dump user/recommendation feedback from postgres into spark format.

        Arguments:
            location: Directory where the final dump will be stored
            dump_time: datetime object representing when the dump was started
            threads: Maximal number of threads to run during compression

        Returns:
            path to feedback dump
    """

    current_app.logger.info('Beginning dump of feedback data...')
    current_app.logger.info('dump path: %s', location)
    try:
        feedback_dump = create_feedback_dump(location, dump_time, threads)
    except IOError as e:
        current_app.logger.critical(
            'IOError while creating feedback dump: %s', str(e), exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return
    except Exception as e:
        current_app.logger.critical(
            'Unable to create feedback dump due to error %s', str(e), exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return

    current_app.logger.info(
        'Dump of feedback data created at %s!', feedback_dump)

    return feedback_dump


def _create_dump(location, dump_type, tables, dump_time, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Creates a dump of the provided tables at the location passed

        Arguments:
            location: the path where the dump should be created
            dump_type: the type of data dump being made - private or public
            tables: a dict containing the names of the tables to be dumped as keys and the columns
                    to be dumped as values
            dump_time: the time at which the dump process was started
            threads: the maximum number of threads to use for compression

        Returns:
            the path to the archive file created
    """

    archive_name = 'listenbrainz-{dump_type}-dump-{time}'.format(
        dump_type=dump_type,
        time=dump_time.strftime('%Y%m%d-%H%M%S')
    )
    archive_path = os.path.join(location, '{archive_name}.tar.xz'.format(
        archive_name=archive_name,
    ))

    with open(archive_path, 'w') as archive:

        pxz_command = ['pxz', '--compress',
                       '-T{threads}'.format(threads=threads)]
        pxz = subprocess.Popen(
            pxz_command, stdin=subprocess.PIPE, stdout=archive)

        with tarfile.open(fileobj=pxz.stdin, mode='w|') as tar:

            temp_dir = tempfile.mkdtemp()

            try:
                schema_seq_path = os.path.join(temp_dir, "SCHEMA_SEQUENCE")
                with open(schema_seq_path, "w") as f:
                    f.write(str(db.SCHEMA_VERSION))
                tar.add(schema_seq_path,
                        arcname=os.path.join(archive_name, "SCHEMA_SEQUENCE"))
                timestamp_path = os.path.join(temp_dir, "TIMESTAMP")
                with open(timestamp_path, "w") as f:
                    f.write(dump_time.isoformat(" "))
                tar.add(timestamp_path,
                        arcname=os.path.join(archive_name, "TIMESTAMP"))
                tar.add(DUMP_LICENSE_FILE_PATH,
                        arcname=os.path.join(archive_name, "COPYING"))
            except IOError as e:
                current_app.logger.error(
                    'IOError while adding dump metadata: %s', str(e), exc_info=True)
                raise
            except Exception as e:
                current_app.logger.error(
                    'Exception while adding dump metadata: %s', str(e), exc_info=True)
                raise

            archive_tables_dir = os.path.join(temp_dir, 'lbdump', 'lbdump')
            create_path(archive_tables_dir)

            with db.engine.connect() as connection:
                if dump_type == "feedback":
                    dump_user_feedback(connection, location=archive_tables_dir)
                else:
                    with connection.begin() as transaction:
                        cursor = connection.connection.cursor()
                        for table in tables:
                            try:
                                copy_table(
                                    cursor=cursor,
                                    location=archive_tables_dir,
                                    columns=','.join(tables[table]),
                                    table_name=table,
                                )
                            except IOError as e:
                                current_app.logger.error(
                                    'IOError while copying table %s', table, exc_info=True)
                                raise
                            except Exception as e:
                                current_app.logger.error(
                                    'Error while copying table %s: %s', table, str(e), exc_info=True)
                                raise
                        transaction.rollback()

            tar.add(archive_tables_dir, arcname=os.path.join(
                archive_name, 'lbdump'.format(dump_type)))

            shutil.rmtree(temp_dir)

        pxz.stdin.close()

    pxz.wait()
    return archive_path


def create_private_dump(location, dump_time, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create postgres database dump for private data in db.
        This includes dumps of the following tables:
            "user",
            api_compat.token,
            api_compat.session
    """
    return _create_dump(
        location=location,
        dump_type='private',
        tables=PRIVATE_TABLES,
        dump_time=dump_time,
        threads=threads,
    )


def create_public_dump(location, dump_time, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create postgres database dump for statistics and user info in db.
        This includes a sanitized dump of the "user" table and dumps of all tables
        in the statistics schema:
            statistics.user
            statistics.artist
            statistics.release
            statistics.recording
    """
    return _create_dump(
        location=location,
        dump_type='public',
        tables=PUBLIC_TABLES,
        dump_time=dump_time,
        threads=threads,
    )


def create_feedback_dump(location, dump_time, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create a spark format dump of user listen and user recommendation feedback.
    """
    return _create_dump(
        location=location,
        dump_type='feedback',
        tables=[],
        dump_time=dump_time,
        threads=threads,
    )


def dump_user_feedback(connection, location):
    """ Carry out the actual dumping of user listen and user recommendation feedback.
    """

    with connection.begin() as transaction:

        # First dump the user feedback
        result = connection.execute(sqlalchemy.text("""
            SELECT musicbrainz_id, recording_msid, score, r.created,
                   EXTRACT(YEAR FROM r.created) AS year,
                   EXTRACT(MONTH FROM r.created) AS month,
                   EXTRACT(DAY FROM r.created) AS day
              FROM recording_feedback r
              JOIN "user"
                ON r.user_id = "user".id
          ORDER BY created"""))

        last_day = ()
        todays_items = []

        while True:
            row = result.fetchone()
            today = (row[4], row[5], row[6]) if row else ()
            if (not row or today != last_day) and len(todays_items) > 0:
                full_path = os.path.join(location, "feedback", "listens", "%02d" % int(last_day[0]),
                                         "%02d" % int(last_day[1]), "%02d" % int(last_day[2]))
                os.makedirs(full_path)
                with open(os.path.join(full_path, "data.json"), "wb") as f:
                    for item in todays_items:
                        f.write(bytes(ujson.dumps(item) + "\n", "utf-8"))
                todays_items = []

            if not row:
                break

            todays_items.append({'user_name': row[0],
                                 'recording_msid': str(row[1]),
                                 'feedback': row[2],
                                 'created': row[3].isoformat()})
            last_day = today

        # Now dump the recommendation feedback
        result = connection.execute(sqlalchemy.text("""
            SELECT musicbrainz_id, recording_mbid, rating, r.created,
                   EXTRACT(YEAR FROM r.created) AS year,
                   EXTRACT(MONTH FROM r.created) AS month,
                   EXTRACT(DAY FROM r.created) AS day
              FROM recommendation_feedback r
              JOIN "user"
                ON r.user_id = "user".id
          ORDER BY created"""))

        last_day = ()
        todays_items = []

        while True:
            row = result.fetchone()
            today = (row[4], row[5], row[6]) if row else ()
            if (not row or today != last_day) and len(todays_items) > 0:
                full_path = os.path.join(location, "feedback", "recommendation", "%02d" % int(last_day[0]),
                                         "%02d" % int(last_day[1]), "%02d" % int(last_day[2]))
                os.makedirs(full_path)
                with open(os.path.join(full_path, "data.json"), "wb") as f:
                    for item in todays_items:
                        f.write(bytes(ujson.dumps(item) + "\n", "utf-8"))
                todays_items = []

            if not row:
                break

            todays_items.append({'user_name': row[0],
                                 'mb_recording_mbid': str(row[1]),
                                 'feedback': row[2],
                                 'created': row[3].isoformat()})
            last_day = today
        transaction.rollback()


def copy_table(cursor, location, columns, table_name):
    """ Copies a PostgreSQL table to a file

        Arguments:
            cursor: a psycopg cursor
            location: the directory where the table should be copied
            columns: a comma seperated string listing the columns of the table
                     that should be dumped
            table_name: the name of the table to be copied
    """

    with open(os.path.join(location, table_name), 'w') as f:
        cursor.copy_to(f, '(SELECT {columns} FROM {table})'.format(
            columns=columns,
            table=table_name
        ))


def add_dump_entry(timestamp):
    """ Adds an entry to the data_dump table with specified time.

        Args:
            timestamp: the unix timestamp to be added

        Returns:
            id (int): the id of the new entry added
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                INSERT INTO data_dump (created)
                     VALUES (TO_TIMESTAMP(:ts))
                  RETURNING id
            """), {
            'ts': timestamp,
        })
        return result.fetchone()['id']


def get_dump_entries():
    """ Returns a list of all dump entries in the data_dump table
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                SELECT id, created
                  FROM data_dump
              ORDER BY created DESC
            """))

        return [dict(row) for row in result]


def get_dump_entry(dump_id):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created
              FROM data_dump
             WHERE id = :dump_id
        """), {
            'dump_id': dump_id,
        })
        if result.rowcount > 0:
            return dict(result.fetchone())
        return None


def import_postgres_dump(private_dump_archive_path=None, public_dump_archive_path=None, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Imports postgres dump created by dump_postgres_db present at location.

        Arguments:
            location: the directory where the private and public archives are present
            threads: the number of threads to use while decompressing the archives, defaults to
                     db.DUMP_DEFAULT_THREAD_COUNT
    """

    if private_dump_archive_path:
        current_app.logger.info(
            'Importing private dump %s...', private_dump_archive_path)
        try:
            _import_dump(private_dump_archive_path,
                         'private', PRIVATE_TABLES, threads)
            current_app.logger.info(
                'Import of private dump %s done!', private_dump_archive_path)
        except IOError as e:
            current_app.logger.critical(
                'IOError while importing private dump: %s', str(e), exc_info=True)
            raise
        except SchemaMismatchException as e:
            current_app.logger.critical(
                'SchemaMismatchException: %s', str(e), exc_info=True)
            raise
        except Exception as e:
            current_app.logger.critical(
                'Error while importing private dump: %s', str(e), exc_info=True)
            raise
        current_app.logger.info(
            'Private dump %s imported!', private_dump_archive_path)

    if public_dump_archive_path:
        current_app.logger.info(
            'Importing public dump %s...', public_dump_archive_path)

        tables_to_import = PUBLIC_TABLES.copy()
        if private_dump_archive_path:
            # if the private dump exists and has been imported, we need to
            # ignore the sanitized user table in the public dump
            # so remove it from tables_to_import
            del tables_to_import['"user"']

        try:
            _import_dump(public_dump_archive_path, 'public',
                         tables_to_import, threads)
            current_app.logger.info(
                'Import of Public dump %s done!', public_dump_archive_path)
        except IOError as e:
            current_app.logger.critical(
                'IOError while importing public dump: %s', str(e), exc_info=True)
            raise
        except SchemaMismatchException as e:
            current_app.logger.critical(
                'SchemaMismatchException: %s', str(e), exc_info=True)
            raise
        except Exception as e:
            current_app.logger.critical(
                'Error while importing public dump: %s', str(e), exc_info=True)
            raise
        current_app.logger.info(
            'Public dump %s imported!', public_dump_archive_path)


def _import_dump(archive_path, dump_type, tables, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Import dump present in passed archive path into postgres db.

        Arguments:
            archive_path: path to the .tar.xz archive to be imported
            dump_type (str): type of dump to be imported ('private' or 'public')
            tables: dict of tables present in the archive with table name as key and
                    columns to import as values
            threads (int): the number of threads to use while decompressing, defaults to
                            db.DUMP_DEFAULT_THREAD_COUNT
    """

    pxz_command = ['pxz', '--decompress', '--stdout',
                   archive_path, '-T{threads}'.format(threads=threads)]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

    connection = db.engine.raw_connection()
    try:
        cursor = connection.cursor()
        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            for member in tar:
                file_name = member.name.split('/')[-1]

                if file_name == 'SCHEMA_SEQUENCE':
                    # Verifying schema version
                    schema_seq = int(tar.extractfile(member).read().strip())
                    if schema_seq != db.SCHEMA_VERSION:
                        raise SchemaMismatchException('Incorrect schema version! Expected: %d, got: %d.'
                                                      'Please, get the latest version of the dump.'
                                                      % (db.SCHEMA_VERSION, schema_seq))
                    else:
                        current_app.logger.info('Schema version verified.')

                else:
                    if file_name in tables:
                        current_app.logger.info(
                            'Importing data into %s table...', file_name)
                        try:
                            cursor.copy_from(tar.extractfile(member), '%s' % file_name,
                                             columns=tables[file_name])
                            connection.commit()
                        except IOError as e:
                            current_app.logger.critical(
                                'IOError while extracting table %s: %s', file_name, str(e), exc_info=True)
                            raise
                        except Exception as e:
                            current_app.logger.critical(
                                'Exception while importing table %s: %s', file_name, str(e), exc_info=True)
                            raise

                        current_app.logger.info('Imported table %s', file_name)
    finally:
        connection.close()
        pxz.stdout.close()

    try:
        _update_sequences()
    except Exception as e:
        current_app.logger.critical(
            'Exception while trying to update sequences: %s', str(e), exc_info=True)
        raise


def _update_sequence(seq_name, table_name):
    """ Update the specified sequence's value to the maximum value of ID in the table.

    Args:
        seq_name (str): the name of the sequence to be updated.
        table_name (str): the name of the table from which the maximum value is to be retrieved
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            SELECT setval('{seq_name}', max(id))
              FROM {table_name}
        """.format(seq_name=seq_name, table_name=table_name)))


def _update_sequences():
    """ Update all sequences to the maximum value of id in the table.
    """
    # user_id_seq
    current_app.logger.info('Updating user_id_seq...')
    _update_sequence('user_id_seq', '"user"')

    # token_id_seq
    current_app.logger.info('Updating token_id_seq...')
    _update_sequence('api_compat.token_id_seq', 'api_compat.token')

    # session_id_seq
    current_app.logger.info('Updating session_id_seq...')
    _update_sequence('api_compat.session_id_seq', 'api_compat.session')

    # artist_id_seq
    current_app.logger.info('Updating artist_id_seq...')
    _update_sequence('statistics.artist_id_seq', 'statistics.artist')

    # release_id_seq
    current_app.logger.info('Updating release_id_seq...')
    _update_sequence('statistics.release_id_seq', 'statistics.release')

    # recording_id_seq
    current_app.logger.info('Updating recording_id_seq...')
    _update_sequence('statistics.recording_id_seq', 'statistics.recording')

    # data_dump_id_seq
    current_app.logger.info('Updating data_dump_id_seq...')
    _update_sequence('data_dump_id_seq', 'data_dump')


def _fetch_latest_file_info_from_ftp_dir(server, dir):
    """
        Given a FTP server and dir, fetch the latst dump file info, parse it and
        return a tuple containing (dump_id, datetime_of_dump_file).
    """

    line = ""

    def add_line(l):
        nonlocal line
        l = l.strip()
        if l:
            line = l

    ftp = FTP(server)
    ftp.login()
    ftp.cwd(dir)
    ftp.retrlines('LIST', add_line)
    _, _, id, d, t, _ = line[56:].strip().split("-")

    return int(id), datetime.strptime(d + t, "%Y%m%d%H%M%S")


def check_ftp_dump_ages():
    """
        Fetch the FTP dir listing of the full and incremental dumps and check their ages. Send mail
        to the observability list in case the dumps are too old.
    """

    msg = ""
    try:
        id, dt = _fetch_latest_file_info_from_ftp_dir(
            MAIN_FTP_SERVER_URL, '/pub/musicbrainz/listenbrainz/fullexport')
        age = datetime.now() - dt
        if age > timedelta(days=FULLEXPORT_MAX_AGE):
            msg = "Full dump %d is more than %d days old: %s\n" % (
                id, FULLEXPORT_MAX_AGE, str(age))
            print(msg, end="")
        else:
            print("Full dump %s is %s old, good!" % (id, str(age)))
    except Exception as err:
        msg = "Cannot fetch full dump age: %s" % str(err)

    try:
        id, dt = _fetch_latest_file_info_from_ftp_dir(
            MAIN_FTP_SERVER_URL, '/pub/musicbrainz/listenbrainz/incremental')
        age = datetime.now() - dt
        if age > timedelta(hours=INCREMENTAL_MAX_AGE):
            msg = "Incremental dump %s is more than %s hours old: %s\n" % (
                id, INCREMENTAL_MAX_AGE, str(age))
            print(msg, end="")
        else:
            print("Incremental dump %s is %s old, good!" % (id, str(age)))
    except Exception as err:
        msg = "Cannot fetch full dump age: %s" % str(err)

    app = create_app()
    with app.app_context():
        if not current_app.config['TESTING'] and msg:
            send_mail(
                subject="ListenBrainz outdated dumps!",
                text=render_template('emails/data_dump_outdated.txt', msg=msg),
                recipients=['listenbrainz-exceptions@metabrainz.org'],
                from_name='ListenBrainz',
                from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN']
            )


class SchemaMismatchException(Exception):
    pass
