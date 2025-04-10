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
import traceback
from datetime import datetime, timedelta
from ftplib import FTP
from typing import Tuple, Optional

import sqlalchemy
import orjson
from brainzutils.mail import send_mail
from flask import current_app, render_template
from psycopg2.sql import Identifier, SQL, Composable

import listenbrainz.db as db
from data.model.common_stat import ALLOWED_STATISTICS_RANGE
from listenbrainz import DUMP_LICENSE_FILE_PATH
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.db import timescale, couchdb
from listenbrainz.utils import create_path
from listenbrainz.webserver import create_app

MAIN_FTP_SERVER_URL = "ftp.eu.metabrainz.org"
FULLEXPORT_MAX_AGE = 17  # days
INCREMENTAL_MAX_AGE = 26  # hours
FEEDBACK_MAX_AGE = 8  # days

# this dict contains the tables dumped in public dump as keys
# and a tuple of columns that should be dumped as values
PUBLIC_TABLES_DUMP = {
    'user': (
        'id',
        'created',
        'musicbrainz_id',
        'musicbrainz_row_id',
        # the following are dummy values for columns that we do not want to dump in the public dump
        # for items that are not columns or need manual quoting, wrap in SQL/Literal accordingly here
        SQL('null'),  # auth token
        SQL('to_timestamp(0)'),  # last_login
        SQL('to_timestamp(0)'),  # latest_import
    ),
    'recording_feedback': (
        'id',
        'user_id',
        'recording_msid',
        'recording_mbid',
        'score',
        'created'
    ),
    'pinned_recording': (
        'id',
        'user_id',
        'recording_msid',
        'recording_mbid',
        'blurb_content',
        'pinned_until',
        'created'
    ),
    'user_relationship': (
        'user_0',
        'user_1',
        'relationship_type',
        'created'
    ),
}

PUBLIC_TABLES_TIMESCALE_DUMP = {
    'mbid_mapping_metadata': (
        'artist_credit_id',
        'recording_mbid',
        'release_mbid',
        'release_name',
        'artist_mbids',
        'artist_credit_name',
        'recording_name',
        'last_updated',
    ),
    'mbid_mapping': (
        'recording_msid',
        'recording_mbid',
        'match_type',
        'last_updated',
        'check_again',
    ),
    'mbid_manual_mapping': (
        'id',
        'recording_msid',
        'recording_mbid',
        'user_id',
        'created',
    ),
    'messybrainz.submissions': (
        'id',
        'gid',
        'recording',
        'artist_credit',
        'release',
        'track_number',
        'duration',
        'submitted',
    ),
}

PUBLIC_TABLES_IMPORT = PUBLIC_TABLES_DUMP.copy()
# When importing fields with COPY we need to use the names of the fields, rather
# than the placeholders that we set for the export
PUBLIC_TABLES_IMPORT['user'] = (
        'id',
        'created',
        'musicbrainz_id',
        'musicbrainz_row_id',
        'auth_token',
        'last_login',
        'latest_import',
    )

# this dict contains the tables dumped in the private dump as keys
# and a tuple of columns that should be dumped as values
PRIVATE_TABLES = {
    'user': (
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
    'reported_users': (
        'id',
        'reporter_user_id',
        'reported_user_id',
        'reported_at',
        'reason'
    ),
    'external_service_oauth': (
        'id',
        'user_id',
        'service',
        'access_token',
        'refresh_token',
        'token_expires',
        'last_updated',
        'scopes'
    ),
    'listens_importer': (
        'id',
        'external_service_oauth_id',
        'user_id',
        'service',
        'last_updated',
        'latest_listened_at',
        'error_message'
    ),
    'user_setting': (
        'id',
        'user_id',
        'timezone_name',
        'troi',
        'brainzplayer',
    ),
    'user_timeline_event': (
        'id',
        'user_id',
        'event_type',
        'metadata',
        'created',
    ),
    'hide_user_timeline_event': (
        'id',
        'user_id',
        'event_type',
        'event_id',
        'created',
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

PRIVATE_TABLES_TIMESCALE = {
    'playlist.playlist': (
        'id',
        'mbid',
        'creator_id',
        'name',
        'description',
        'public',
        'created',
        'last_updated',
        'copied_from_id',
        'created_for_id',
        'additional_metadata',
    ),
    'playlist.playlist_recording': (
        'id',
        'playlist_id',
        'position',
        'mbid',
        'added_by_id',
        'created'
    ),
    'playlist.playlist_collaborator': (
        'playlist_id',
        'collaborator_id'
    )
}


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
        schema_version=db.SCHEMA_VERSION_CORE,
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
        schema_version=db.SCHEMA_VERSION_CORE,
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
        schema_version=db.SCHEMA_VERSION_CORE,
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
        schema_version=db.SCHEMA_VERSION_CORE,
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


def add_dump_entry(timestamp, dump_type):
    """ Adds an entry to the data_dump table with specified time.

        Args:
            timestamp: the datetime to be added

        Returns:
            id (int): the id of the new entry added
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
                INSERT INTO data_dump (created, dump_type)
                     VALUES (:ts, :dump_type)
                  RETURNING id
            """), {
            'ts': timestamp,
            'dump_type': dump_type
        })
        return result.fetchone().id


def get_dump_entries():
    """ Returns a list of all dump entries in the data_dump table
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                SELECT id, created, dump_type
                  FROM data_dump
              ORDER BY created DESC
            """))

        return result.mappings().all()


def get_dump_entry(dump_id, dump_type=None):
    filters = ["id = :dump_id"]
    args = {"dump_id": dump_id}

    if dump_type is not None:
        filters.append("dump_type = :dump_type")
        args["dump_type"] = dump_type

    where_clause = " AND ".join(filters)
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, dump_type
              FROM data_dump
             WHERE """ + where_clause), args)
        return result.mappings().first()


def get_latest_incremental_dump():
    """ Get the latest incremental dump"""
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, dump_type
              FROM data_dump
             WHERE dump_type = 'incremental'
          ORDER BY id DESC
             LIMIT 1
        """))
        return result.mappings().first()


def get_previous_incremental_dump(dump_id):
    """ Get the id of the incremental dump that is one before the given dump id.

    Cannot just do dump_id - 1 because SERIAL/IDENTITY columns in postgres can skip values in some
    cases (for instance master/standby switchover).
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, dump_type
              FROM data_dump
             WHERE id < :dump_id
               AND dump_type = 'incremental'
          ORDER BY id DESC
             LIMIT 1
        """), {"dump_id": dump_id})
        return result.mappings().first()


def import_postgres_dump(private_dump_archive_path=None,
                         private_timescale_dump_archive_path=None,
                         public_dump_archive_path=None,
                         public_timescale_dump_archive_path=None,
                         threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Imports postgres dump created by dump_postgres_db present at location.

        Arguments:
            private_dump_archive_path: Location of the private dump file
            private_timescale_dump_archive_path: Location of the private timescale dump file
            public_dump_archive_path: Location of the public dump file
            public_timescale_dump_archive_path: Location of the public timescale dump file
            threads: the number of threads to use while decompressing the archives, defaults to
                     db.DUMP_DEFAULT_THREAD_COUNT
    """

    if private_dump_archive_path:
        current_app.logger.info('Importing private dump %s...', private_dump_archive_path)
        _import_dump(private_dump_archive_path, db.engine, PRIVATE_TABLES, db.SCHEMA_VERSION_CORE, threads)
        current_app.logger.info('Import of private dump %s done!', private_dump_archive_path)

    if private_timescale_dump_archive_path:
        current_app.logger.info('Importing private timescale dump %s...', private_timescale_dump_archive_path)
        _import_dump(private_timescale_dump_archive_path, timescale.engine, PRIVATE_TABLES_TIMESCALE,
                     timescale.SCHEMA_VERSION_TIMESCALE, threads)
        current_app.logger.info('Import of private timescale dump %s done!', private_timescale_dump_archive_path)

    if public_dump_archive_path:
        current_app.logger.info('Importing public dump %s...', public_dump_archive_path)

        tables_to_import = PUBLIC_TABLES_IMPORT.copy()
        if private_dump_archive_path:
            # if the private dump exists and has been imported, we need to
            # ignore the sanitized user table in the public dump
            # so remove it from tables_to_import
            del tables_to_import['user']

        _import_dump(public_dump_archive_path, db.engine, tables_to_import, db.SCHEMA_VERSION_CORE, threads)
        current_app.logger.info('Import of Public dump %s done!', public_dump_archive_path)

    if public_timescale_dump_archive_path:
        current_app.logger.info('Importing public timescale dump %s...', public_timescale_dump_archive_path)
        _import_dump(public_timescale_dump_archive_path, timescale.engine, PUBLIC_TABLES_TIMESCALE_DUMP,
                     timescale.SCHEMA_VERSION_TIMESCALE, threads)
        current_app.logger.info('Import of Public timescale dump %s done!', public_timescale_dump_archive_path)

    try:
        current_app.logger.info("Creating sequences")
        _update_sequences()
    except Exception:
        current_app.logger.critical('Exception while trying to update sequences: ', exc_info=True)
        raise


def _escape_table_columns(table: str, columns: list[str | Composable]) \
        -> tuple[Composable, Composable]:
    """
    Escape the given table name and columns/values if those are not already escaped.

    Args:
        table: name of the table
        columns: list of column names or values

    Returns:
        tuple consisting of properly escaped table name and joined columns
    """
    fields = []
    for column in columns:
        # Composable is the base class for all types of escaping in psycopg2.sql
        # therefore, instances of Composable are already escaped and should be
        # passed as is. for all other cases, escape as an Identifier which is the
        # type used to escape column names, table names etc.
        if isinstance(column, Composable):
            fields.append(column)
        else:
            fields.append(Identifier(column))
    joined_fields = SQL(',').join(fields)

    # for schema qualified table names, need to pass schema and table name as
    # separate args therefore the split
    escaped_table_name = Identifier(*table.split("."))

    return escaped_table_name, joined_fields


def _import_dump(archive_path, db_engine: sqlalchemy.engine.Engine,
                 tables, schema_version: int, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Import dump present in passed archive path into postgres db.

        Arguments:
            archive_path: path to the .tar.zst archive to be imported
            db_engine: an sqlalchemy Engine instance for making a connection
            tables: dict of tables present in the archive with table name as key and
                    columns to import as values
            schema_version: the current schema version, to compare against the dumped file
            threads (int): the number of threads to use while decompressing, defaults to
                            db.DUMP_DEFAULT_THREAD_COUNT
    """

    zstd_command = ['zstd', '--decompress', '--stdout', archive_path, f'-T{threads}']
    zstd = subprocess.Popen(zstd_command, stdout=subprocess.PIPE)

    connection = db_engine.raw_connection()
    try:
        cursor = connection.cursor()
        with tarfile.open(fileobj=zstd.stdout, mode='r|') as tar:
            for member in tar:
                file_name = member.name.split('/')[-1]

                if file_name == 'SCHEMA_SEQUENCE':
                    # Verifying schema version
                    schema_seq = int(tar.extractfile(member).read().strip())
                    if schema_seq != schema_version:
                        raise SchemaMismatchException('Incorrect schema version! Expected: %d, got: %d.'
                                                      'Please, get the latest version of the dump.'
                                                      % (schema_version, schema_seq))
                    else:
                        current_app.logger.info('Schema version verified.')

                else:
                    if file_name in tables:
                        current_app.logger.info('Importing data into %s table...', file_name)
                        try:
                            table, fields = _escape_table_columns(file_name, tables[file_name])
                            query = SQL("COPY {table}({fields}) FROM STDIN").format(fields=fields, table=table)
                            cursor.copy_expert(query, tar.extractfile(member))
                            connection.commit()
                        except Exception:
                            current_app.logger.critical('Exception while importing table %s: ', file_name, exc_info=True)
                            raise

                        current_app.logger.info('Imported table %s', file_name)
    finally:
        connection.close()
        zstd.stdout.close()


def _update_sequence(db_engine: sqlalchemy.engine.Engine, seq_name, table_name):
    """ Update the specified sequence's value to the maximum value of ID in the table.

    Args:
        seq_name (str): the name of the sequence to be updated.
        table_name (str): the name of the table from which the maximum value is to be retrieved
    """
    with db_engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            SELECT setval('{seq_name}', max(id))
              FROM {table_name}
        """.format(seq_name=seq_name, table_name=table_name)))


def _update_sequences():
    """ Update all sequences to the maximum value of id in the table.
    """
    # user_id_seq
    current_app.logger.info('Updating user_id_seq...')
    _update_sequence(db.engine, 'user_id_seq', '"user"')

    # external_service_oauth_id_seq
    current_app.logger.info('Updating external_service_oauth_id_seq...')
    _update_sequence(db.engine, 'external_service_oauth_id_seq', 'external_service_oauth')

    # listens_importer_id_seq
    current_app.logger.info('Updating listens_importer_id_seq...')
    _update_sequence(db.engine, 'listens_importer_id_seq', 'listens_importer')

    # token_id_seq
    current_app.logger.info('Updating token_id_seq...')
    _update_sequence(db.engine, 'api_compat.token_id_seq', 'api_compat.token')

    # session_id_seq
    current_app.logger.info('Updating session_id_seq...')
    _update_sequence(db.engine, 'api_compat.session_id_seq', 'api_compat.session')

    # data_dump_id_seq
    current_app.logger.info('Updating data_dump_id_seq...')
    _update_sequence(db.engine, 'data_dump_id_seq', 'data_dump')

    current_app.logger.info('Updating playlist.playlist_id_seq...')
    _update_sequence(timescale.engine, 'playlist.playlist_id_seq', 'playlist.playlist')

    current_app.logger.info('Updating playlist.playlist_recording_id_seq...')
    _update_sequence(timescale.engine, 'playlist.playlist_recording_id_seq', 'playlist.playlist_recording')


def _fetch_latest_file_info_from_ftp_dir(directory: str, has_id: bool):
    """
        Given a base FTP dir and whether the dump name contains an id, browses the MB FTP server to fetch
        the latest dump directory name and return it
    """

    latest_dump_id: Optional[int] = None
    latest_dt: Optional[datetime] = None

    def process_line(file):
        nonlocal latest_dump_id, latest_dt
        if file:
            if has_id:
                dump_id, dt = _parse_ftp_name_with_id(file)
            else:
                dump_id, dt = _parse_ftp_name_without_id(file)

            if latest_dt is None or dt > latest_dt:
                latest_dt = dt
                latest_dump_id = dump_id

    ftp = FTP(MAIN_FTP_SERVER_URL)
    ftp.login()
    ftp.cwd(directory)
    ftp.retrlines('NLST', process_line)

    return latest_dump_id, latest_dt


def _parse_ftp_name_with_id(name):
    """Parse a name like
        listenbrainz-dump-712-20220201-040003-full
    into its id (712), and a datetime.datetime object representing the datetime (2022-02-01 04:00:03)

    Returns:
        a tuple (id, datetime of file)
    """
    parts = name.split("-")
    if len(parts) != 6:
        raise ValueError("Filename '{}' expected to have 6 parts separated by -".format(name))
    _, _, dumpid, d, t, _ = parts
    return int(dumpid), datetime.strptime(d + t, "%Y%m%d%H%M%S")


def _parse_ftp_name_without_id(name):
    """Parse a name like
        listenbrainz-feedback-20220207-060003-full
    into an id (20220207-060003), and a datetime.datetime object representing the datetime (2022-02-07 06:00:03)

    Returns:
        a tuple (id, datetime of file)
    """
    parts = name.split("-")
    if len(parts) != 5:
        raise ValueError("Filename '{}' expected to have 5 parts separated by -".format(name))
    _, _, d, t, _ = parts
    return d + '-' + t, datetime.strptime(d + t, "%Y%m%d%H%M%S")


def check_ftp_dump_ages():
    """
        Fetch the FTP dir listing of the full and incremental dumps and check their ages. Send mail
        to the observability list in case the dumps are too old.
    """

    msg = ""
    try:
        dump_id, dt = _fetch_latest_file_info_from_ftp_dir('/pub/musicbrainz/listenbrainz/fullexport', True)
        age = datetime.now() - dt
        if age > timedelta(days=FULLEXPORT_MAX_AGE):
            msg = "Full dump %d is more than %d days old: %s\n" % (dump_id, FULLEXPORT_MAX_AGE, str(age))
            print(msg, end="")
        else:
            print("Full dump %s is %s old, good!" % (dump_id, str(age)))
    except Exception as err:
        msg = "Cannot fetch full dump age: %s\n\n%s" % (str(err), traceback.format_exc())

    try:
        dump_id, dt = _fetch_latest_file_info_from_ftp_dir('/pub/musicbrainz/listenbrainz/incremental', True)
        age = datetime.now() - dt
        if age > timedelta(hours=INCREMENTAL_MAX_AGE):
            msg = "Incremental dump %s is more than %s hours old: %s\n" % (dump_id, INCREMENTAL_MAX_AGE, str(age))
            print(msg, end="")
        else:
            print("Incremental dump %s is %s old, good!" % (dump_id, str(age)))
    except Exception as err:
        msg = "Cannot fetch incremental dump age: %s\n\n%s" % (str(err), traceback.format_exc())

    try:
        dump_id, dt = _fetch_latest_file_info_from_ftp_dir('/pub/musicbrainz/listenbrainz/spark', False)
        age = datetime.now() - dt
        if age > timedelta(days=FEEDBACK_MAX_AGE):
            msg = "Feedback dump %s is more than %s days old: %s\n" % (dump_id, FEEDBACK_MAX_AGE, str(age))
            print(msg, end="")
        else:
            print("Feedback dump %s is %s old, good!" % (dump_id, str(age)))
    except Exception as err:
        msg = "Cannot fetch feedback dump age: %s\n\n%s" % (str(err), traceback.format_exc())

    app = create_app()
    with app.app_context():
        if not current_app.config['TESTING'] and msg:
            send_mail(
                subject="ListenBrainz outdated dumps!",
                text=render_template('emails/data_dump_outdated.txt', msg=msg),
                recipients=['listenbrainz-exceptions@metabrainz.org'],
                from_name='ListenBrainz',
                from_addr='noreply@' + current_app.config['MAIL_FROM_DOMAIN']
            )
        elif msg:
            print(msg)


class SchemaMismatchException(Exception):
    pass
