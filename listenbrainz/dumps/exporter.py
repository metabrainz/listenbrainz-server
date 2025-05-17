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
from typing import Tuple, Optional

import orjson
import sqlalchemy
from flask import current_app
from psycopg2.sql import SQL

import listenbrainz.db as db
import listenbrainz.dumps
from data.model.common_stat import ALLOWED_STATISTICS_RANGE
from listenbrainz import DUMP_LICENSE_FILE_PATH
from listenbrainz.db import timescale, couchdb
from listenbrainz.dumps import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.dumps.tables import _escape_table_columns, PUBLIC_TABLES_TIMESCALE_DUMP, PUBLIC_TABLES_DUMP, \
    PRIVATE_TABLES_TIMESCALE, PRIVATE_TABLES
from listenbrainz.utils import create_path


def dump_postgres_db(location, location_private, dump_time=datetime.today(), threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create postgres database dump in the specified location

        Arguments:
            location: Directory where the final public dump will be stored
            location_private: Directory where the final private dump will be stored
            dump_time: datetime object representing when the dump was started
            threads: Maximal number of threads to run during compression

        Returns:
            a tuple: (path to private dump, path to public dump)
    """
    current_app.logger.info('Beginning dump of PostgreSQL database...')
    current_app.logger.info('private dump path: %s', location_private)

    current_app.logger.info('Creating dump of private data...')
    try:
        private_dump = create_private_dump(location_private, dump_time, threads)
    except Exception:
        current_app.logger.critical('Unable to create private db dump due to error: ', exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location_private)
        return
    current_app.logger.info('Dump of private data created at %s!', private_dump)

    current_app.logger.info('public dump path: %s', location)
    current_app.logger.info('Creating dump of public data...')
    try:
        public_dump = create_public_dump(location, dump_time, threads)
    except Exception:
        current_app.logger.critical('Unable to create public dump due to error: ', exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return

    current_app.logger.info('ListenBrainz PostgreSQL data dump created at %s!', location)
    return private_dump, public_dump


def dump_timescale_db(location: str, location_private: str, dump_time: datetime = datetime.today(),
                      threads: int = DUMP_DEFAULT_THREAD_COUNT) -> Optional[Tuple[str, str]]:
    """ Create timescale database (excluding listens) dump in the specified location

        Arguments:
            location: Directory where the final public dump will be stored
            location_private: Directory where the final private dump will be stored
            dump_time: datetime object representing when the dump was started
            threads: Maximal number of threads to run during compression

        Returns:
            a tuple: (path to private dump, path to public dump)
    """
    current_app.logger.info('Beginning dump of Timescale database...')

    current_app.logger.info('Creating dump of timescale private data...')
    try:
        private_timescale_dump = create_private_timescale_dump(location_private, dump_time, threads)
    except Exception:
        current_app.logger.critical('Unable to create private timescale db dump due to error: ', exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location_private)
        return
    current_app.logger.info('Dump of private timescale data created at %s!', private_timescale_dump)

    current_app.logger.info('Creating dump of timescale public data...')
    try:
        public_timescale_dump = create_public_timescale_dump(location, dump_time, threads)
    except Exception:
        current_app.logger.critical('Unable to create public timescale dump due to error: ', exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return

    current_app.logger.info('Dump of public timescale data created at %s!', public_timescale_dump)

    return private_timescale_dump, public_timescale_dump


def dump_feedback_for_spark(location, dump_time=datetime.today(), threads=DUMP_DEFAULT_THREAD_COUNT):
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
    except Exception:
        current_app.logger.critical('Unable to create feedback dump due to error: ', exc_info=True)
        current_app.logger.info('Removing created files and giving up...')
        shutil.rmtree(location)
        return

    current_app.logger.info('Dump of feedback data created at %s!', feedback_dump)

    return feedback_dump


def dump_statistics(location: str):
    # TODO: when adding support to dump entity listener statistics, replace user_id with user_name
    stats = [
        f"{stat_type}_{stat_range}"
        # not including aritst_map because those databases are always incomplete we only generate it on demand
        for stat_type in ["artists", "recordings", "releases", "daily_activity", "listening_activity"]
        for stat_range in ALLOWED_STATISTICS_RANGE
    ]
    full_path = os.path.join(location, "statistics")
    for stat in stats:
        try:
            current_app.logger.info(f"Dumping statistics for {stat}...")
            os.makedirs(full_path, exist_ok=True)
            with open(os.path.join(full_path, f"{stat}.jsonl"), "wb+") as fp:
                couchdb.dump_database(stat, fp)
        except Exception:
            current_app.logger.info(f"Failed to create dump for {stat}:", exc_info=True)


def _create_dump(location: str, db_engine: Optional[sqlalchemy.engine.Engine], dump_type: str, tables: Optional[dict],
                 schema_version: int, dump_time: datetime, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Creates a dump of the provided tables at the location passed

        Arguments:
            location: the path where the dump should be created
            db_engine: an sqlalchemy Engine instance for making a connection
            dump_type: the type of data dump being made - private or public
            tables: a dict containing the names of the tables to be dumped as keys and the columns
                    to be dumped as values
            schema_version: the current schema version, to add to the archive file
            dump_time: the time at which the dump process was started
            threads: the maximum number of threads to use for compression

        Returns:
            the path to the archive file created
    """

    archive_name = 'listenbrainz-{dump_type}-dump-{time}'.format(
        dump_type=dump_type,
        time=dump_time.strftime('%Y%m%d-%H%M%S')
    )
    archive_path = os.path.join(location, f'{archive_name}.tar.zst')

    with open(archive_path, 'w') as archive:
        zstd_command = ['zstd', '--compress', f'-T{threads}', '-10']
        zstd = subprocess.Popen(zstd_command, stdin=subprocess.PIPE, stdout=archive)

        with tarfile.open(fileobj=zstd.stdin, mode='w|') as tar:

            temp_dir = tempfile.mkdtemp()

            try:
                schema_seq_path = os.path.join(temp_dir, "SCHEMA_SEQUENCE")
                with open(schema_seq_path, "w") as f:
                    f.write(str(schema_version))
                tar.add(schema_seq_path,
                        arcname=os.path.join(archive_name, "SCHEMA_SEQUENCE"))
                timestamp_path = os.path.join(temp_dir, "TIMESTAMP")
                with open(timestamp_path, "w") as f:
                    f.write(dump_time.isoformat(" "))
                tar.add(timestamp_path,
                        arcname=os.path.join(archive_name, "TIMESTAMP"))
                tar.add(DUMP_LICENSE_FILE_PATH,
                        arcname=os.path.join(archive_name, "COPYING"))
            except Exception:
                current_app.logger.error('Exception while adding dump metadata: ', exc_info=True)
                raise

            archive_tables_dir = os.path.join(temp_dir, 'lbdump', 'lbdump')
            create_path(archive_tables_dir)

            if dump_type == "statistics":
                dump_statistics(archive_tables_dir)
            else:
                with db_engine.connect() as connection:
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
                                        columns=tables[table],
                                        table_name=table,
                                    )
                                except Exception:
                                    current_app.logger.error('Error while copying table %s: ', table, exc_info=True)
                                    raise
                            transaction.rollback()

            if not tables:
                # order doesn't matter or name of tables can't be determined before dumping so just
                # add entire directory with all files inside it
                tar.add(archive_tables_dir, arcname=os.path.join(archive_name, 'lbdump'))
            else:
                # Add the files to the archive in the order that they are defined in the dump definition.
                # This is so that when imported into a db with FK constraints added, we import dependent
                # tables first
                for table in tables:
                    tar.add(os.path.join(archive_tables_dir, table),
                            arcname=os.path.join(archive_name, 'lbdump', table))

            shutil.rmtree(temp_dir)

        zstd.stdin.close()

    zstd.wait()
    return archive_path


def create_private_dump(location: str, dump_time: datetime, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create postgres database dump for private data in db.
        This includes dumps of the following tables:
            "user",
            api_compat.token,
            api_compat.session
    """
    return _create_dump(
        location=location,
        db_engine=db.engine,
        dump_type='private',
        tables=PRIVATE_TABLES,
        schema_version=listenbrainz.dumps.SCHEMA_VERSION_CORE,
        dump_time=dump_time,
        threads=threads,
    )


def create_private_timescale_dump(location: str, dump_time: datetime, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create timescale database dump for private data in db.
    """
    return _create_dump(
        location=location,
        db_engine=timescale.engine,
        dump_type='private-timescale',
        tables=PRIVATE_TABLES_TIMESCALE,
        schema_version=timescale.SCHEMA_VERSION_TIMESCALE,
        dump_time=dump_time,
        threads=threads,
    )


def create_public_dump(location: str, dump_time: datetime, threads=DUMP_DEFAULT_THREAD_COUNT):
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
        db_engine=db.engine,
        dump_type='public',
        tables=PUBLIC_TABLES_DUMP,
        schema_version=listenbrainz.dumps.SCHEMA_VERSION_CORE,
        dump_time=dump_time,
        threads=threads,
    )


def create_public_timescale_dump(location: str, dump_time: datetime, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create postgres database dump for public info in the timescale database.
        This includes the MBID mapping table
    """
    return _create_dump(
        location=location,
        db_engine=timescale.engine,
        dump_type='public-timescale',
        tables=PUBLIC_TABLES_TIMESCALE_DUMP,
        schema_version=timescale.SCHEMA_VERSION_TIMESCALE,
        dump_time=dump_time,
        threads=threads,
    )


def create_feedback_dump(location: str, dump_time: datetime, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create a spark format dump of user listen and user recommendation feedback.
    """
    return _create_dump(
        location=location,
        db_engine=db.engine,
        dump_type='feedback',
        tables=None,
        schema_version=listenbrainz.dumps.SCHEMA_VERSION_CORE,
        dump_time=dump_time,
        threads=threads,
    )


def create_statistics_dump(location: str, dump_time: datetime, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Create couchdb statistics dump. """
    return _create_dump(
        location=location,
        db_engine=None,
        dump_type='statistics',
        tables=None,
        schema_version=listenbrainz.dumps.SCHEMA_VERSION_CORE,
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
                        f.write(orjson.dumps(item))
                        f.write(bytes("\n", "utf-8"))
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
                        f.write(orjson.dumps(item, option=orjson.OPT_APPEND_NEWLINE))
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
    table, fields = _escape_table_columns(table_name, columns)
    with open(os.path.join(location, table_name), 'w') as f:
        query = SQL("COPY (SELECT {fields} FROM {table}) TO STDOUT") \
            .format(fields=fields, table=table)
        cursor.copy_expert(query, f)
