""" This module contains data dump creation and import functions.

Read more about the data dumps in our documentation here:
https://listenbrainz.readthedocs.io/en/latest/users/listenbrainz-dumps.html
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


import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from typing import Optional

import sqlalchemy
from flask import current_app, render_template
from psycopg2.sql import SQL

from listenbrainz import DUMP_LICENSE_FILE_PATH
from brainzutils import musicbrainz_db
from listenbrainz.db import timescale
from listenbrainz.db.dump import _escape_table_columns
from listenbrainz.utils import create_path


PUBLIC_TABLES_MAPPING = {
    'mapping.canonical_musicbrainz_data': {
        'engine': 'lb_if_set',
        'filename': 'canonical_musicbrainz_data.csv',
        'columns': (
            'id',
            'artist_credit_id',
            SQL("array_to_string(artist_mbids, ',') AS artist_mbids"),
            'artist_credit_name',
            'release_mbid',
            'release_name',
            'recording_mbid',
            'recording_name',
            'combined_lookup',
            'score',
        ),
    },
    'mapping.canonical_recording_redirect': {
        'engine': 'lb_if_set',
        'filename': 'canonical_recording_redirect.csv',
        'columns': (
            'recording_mbid',
            'canonical_recording_mbid',
            'canonical_release_mbid'
        )
    },
    'mapping.canonical_release_redirect': {
        'engine': 'lb_if_set',
        'filename': 'canonical_release_redirect.csv',
        'columns': (
            'release_mbid',
            'canonical_release_mbid',
            'release_group_mbid'
        )
    }
}


def _create_dump(location: str, lb_engine: sqlalchemy.engine.Engine, 
                mb_engine: sqlalchemy.engine.Engine, tables: dict,
                dump_time: datetime):
    """ Creates a dump of the provided tables at the location passed

        Arguments:
            location: the path where the dump should be created
            db_engine: an sqlalchemy Engine instance for making a connection
            tables: a dict containing the names of the tables to be dumped as keys and the columns
                    to be dumped as values
            dump_time: the time at which the dump process was started

        Returns:
            the path to the archive file created
    """

    archive_name = 'musicbrainz-canonical-dump-{time}'.format(
        time=dump_time.strftime('%Y%m%d-%H%M%S')
    )
    archive_path = os.path.join(location, '{archive_name}.tar.zst'.format(
        archive_name=archive_name,
    ))

    with open(archive_path, 'w') as archive:

        zstd_command = ["zstd", "--compress", "-10"]
        zstd = subprocess.Popen(zstd_command, stdin=subprocess.PIPE, stdout=archive)

        with tarfile.open(fileobj=zstd.stdin, mode='w|') as tar:

            temp_dir = tempfile.mkdtemp()

            try:
                timestamp_path = os.path.join(temp_dir, "TIMESTAMP")
                with open(timestamp_path, "w") as f:
                    f.write(dump_time.isoformat(" "))
                tar.add(timestamp_path,
                        arcname=os.path.join(archive_name, "TIMESTAMP"))
                tar.add(DUMP_LICENSE_FILE_PATH,
                        arcname=os.path.join(archive_name, "COPYING"))
            except Exception as e:
                current_app.logger.error(
                    'Exception while adding dump metadata: %s', str(e), exc_info=True)
                raise

            archive_tables_dir = os.path.join(temp_dir, 'canonical')
            create_path(archive_tables_dir)

            for table in tables:
                try:
                    engine_name = tables[table]['engine']
                    if engine_name == 'mb':
                        engine = mb_engine
                    elif engine_name == 'lb_if_set' and lb_engine:
                        engine = lb_engine
                    elif engine_name == 'lb_if_set':
                        engine = mb_engine
                    else:
                        raise ValueError(f'Unknown table engine name: {engine_name}')
                    with engine.connect() as connection:
                        with connection.begin() as transaction:
                            cursor = connection.connection.cursor()
                            copy_table(
                                cursor=cursor,
                                location=archive_tables_dir,
                                columns=tables[table]['columns'],
                                table_name=table,
                            )
                            transaction.rollback()
                except Exception as e:
                    current_app.logger.error(
                        'Error while copying table %s: %s', table, str(e), exc_info=True)
                    raise

            # Add the files to the archive in the order that they are defined in the dump definition.
            for table, tabledata in tables.items():
                filename = tabledata['filename']
                tar.add(os.path.join(archive_tables_dir, table),
                        arcname=os.path.join(archive_name, 'canonical', filename))

            shutil.rmtree(temp_dir)

        zstd.stdin.close()

    zstd.wait()
    return archive_path


def create_mapping_dump(location: str, dump_time: datetime, use_lb_conn: bool):
    """ Create postgres database dump of the mapping supplemental tables.
    """
    if use_lb_conn:
        lb_engine = timescale.engine
    else:
        lb_engine = None
    musicbrainz_db.init_db_engine(current_app.config['MB_DATABASE_MAPPING_URI'])
    return _create_dump(
        location=location,
        lb_engine=lb_engine,
        mb_engine=musicbrainz_db.engine,
        tables=PUBLIC_TABLES_MAPPING,
        dump_time=dump_time
    )


def copy_table(cursor, location, columns, table_name):
    """ Copies a PostgreSQL table to a file

        Arguments:
            cursor: a psycopg cursor
            location: the directory where the table should be copied
            columns: a comma seperated string listing the columns of the table
                     that should be dumped
            table_name: the name of the table to be copied
    """
    table, fields = _escape_table_columns(table_name, columns)
    with open(os.path.join(location, table_name), 'w') as f:
        query = SQL("COPY (SELECT {fields} FROM {table}) TO STDOUT WITH CSV HEADER") \
            .format(fields=fields, table=table)
        cursor.copy_expert(query, f)
