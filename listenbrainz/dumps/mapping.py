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
from datetime import datetime

import sqlalchemy
from brainzutils import musicbrainz_db
from flask import current_app

from listenbrainz.db import timescale
from listenbrainz.dumps import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.dumps.exporter import zstd_dump
from listenbrainz.dumps.tables import PUBLIC_TABLES_MAPPING, copy_table
from listenbrainz.utils import create_path


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

    metadata = {"TIMESTAMP": dump_time}
    with zstd_dump(location, archive_name, metadata, DUMP_DEFAULT_THREAD_COUNT) as (zstd, tar, temp_dir, archive_path):
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
                            file_format="csv"
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
