""" This module contains data dump creation and import functions.
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


import listenbrainz.config as config
import listenbrainz.db as db
import logging
import os
import shutil
import sqlalchemy
import subprocess
import sys
import tarfile
import tempfile

from datetime import datetime
from listenbrainz.utils import create_path


DUMP_LICENSE_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                      "licenses", "COPYING-PublicDomain")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

TABLES = {
    '"user"': (
        'id',
        'created',
        'musicbrainz_id',
        'auth_token',
        'last_login',
        'latest_import',
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
    'data_dump': (
        'id',
        'created',
    ),
}


PRIVATE_TABLES = [
    '"user"',
    'api_compat.session',
    'api_compat.token',
]

STATS_TABLES = [
    'statistics.user',
    'statistics.release',
    'statistics.artist',
    'statistics.recording',
]

def dump_postgres_db(location, threads=None):
    """ Create postgres database dump in the specified location

        Arguments:
            location: Directory where the final dump will be stored
            threads: Maximal number of threads to run during compression

        Returns:
            Path to created dump.
    """

    logger.info('Beginning dump of PostgreSQL database...')
    time_now = datetime.today()
    dump_path = os.path.join(location, 'listenbrainz-dump-{time}'.format(time=time_now.strftime('%Y%m%d-%H%M%S')))
    create_path(dump_path)
    logger.info('dump path: %s', dump_path)


    logger.info('Creating dump of private data...')
    private_dump = create_private_dump(dump_path, time_now, threads)
    logger.info('Dump of private data created at %s!', private_dump)

    logger.info('Creating dump of stats data...')
    stats_dump = create_stats_dump(dump_path, time_now, threads)
    logger.info('Dump of stats data created at %s!', stats_dump)


    logger.info('Creating a new entry in the data_dump table...')
    dump_id = add_dump_entry()
    logger.info('New entry with id %d added to data_dump table!', dump_id)

    logger.info('ListenBrainz PostgreSQL data dump created at %s!', dump_path)
    return dump_path


def _create_dump(location, dump_type, tables, time_now, threads=None):
    """ Creates a dump of the provided tables at the location passed

        Arguments:
            location: the path where the dump should be created
            dump_type: the type of data dump being made - private or stats
            tables: a list containing the names of the tables to be dumped
            time_now: the time at which the dump process was started
            threads: the maximum number of threads to use for compression

        Returns:
            the path to the archive file created
    """

    archive_name = 'listenbrainz-{dump_type}-dump-{time}'.format(
        dump_type=dump_type,
        time=time_now.strftime('%Y%m%d-%H%M%S')
    )
    archive_path = os.path.join(location, '{archive_name}.tar.xz'.format(
        archive_name=archive_name,
    ))

    with open(archive_path, 'w') as archive:

        pxz_command = ['pxz', '--compress']
        if threads is not None:
            pxz_command.append('-T {threads}'.format(threads=threads))

        pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

        with tarfile.open(fileobj=pxz.stdin, mode='w|') as tar:

            temp_dir = tempfile.mkdtemp()

            schema_seq_path = os.path.join(temp_dir, "SCHEMA_SEQUENCE")
            with open(schema_seq_path, "w") as f:
                f.write(str(db.SCHEMA_VERSION))
            tar.add(schema_seq_path,
                    arcname=os.path.join(archive_name, "SCHEMA_SEQUENCE"))
            timestamp_path = os.path.join(temp_dir, "TIMESTAMP")
            with open(timestamp_path, "w") as f:
                f.write(time_now.isoformat(" "))
            tar.add(timestamp_path,
                    arcname=os.path.join(archive_name, "TIMESTAMP"))
            tar.add(DUMP_LICENSE_FILE_PATH,
                    arcname=os.path.join(archive_name, "COPYING"))


            archive_tables_dir = os.path.join(temp_dir, 'lb-{}-dump'.format(dump_type), 'lb{}dump'.format(dump_type))
            create_path(archive_tables_dir)


            for table in tables:
                copy_table(archive_tables_dir, table)

            tar.add(archive_tables_dir, arcname=os.path.join(archive_name, 'lb{}dump'.format(dump_type)))

            shutil.rmtree(temp_dir)

        pxz.stdin.close()

    return location


def create_private_dump(location, time_now, threads=None):
    """ Create postgres database dump for private data in db.
        This includes dumps of the following tables:
            "user",
            api_compat.token,
            api_compat.session
    """
    return _create_dump(location, 'private', PRIVATE_TABLES, time_now, threads)


def create_stats_dump(location, time_now, threads=None):
    """ Create postgres database dump for private data in db.
        This includes dumps of the following tables:
            "user",
            api_compat.token,
            api_compat.session
    """
    return _create_dump(location, 'stats', STATS_TABLES, time_now, threads)


def copy_table(location, table_name):
    """ Copies a PostgreSQL table to a file

        Arguments:
            location: the directory where the table should be copied
            table_name: the name of the table to be copied
    """

    connection = db.engine.raw_connection()
    cursor = connection.cursor()

    with open(os.path.join(location, table_name), 'w') as f:
        cursor.copy_to(f, '(SELECT {columns} FROM {table})'.format(
            columns=','.join(TABLES[table_name]),
            table=table_name
        ))

    connection.close()


def add_dump_entry():
    """ Adds an entry to the data_dump table with current time.

        Returns:
            id (int): the id of the new entry added
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                INSERT INTO data_dump (created)
                     VALUES (NOW())
                  RETURNING id
            """))
        return result.fetchone()['id']


if __name__ == '__main__':
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    dump_postgres_db('/dump/')
