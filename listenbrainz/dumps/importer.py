import subprocess
import tarfile

import sqlalchemy
from flask import current_app
from psycopg2.sql import Identifier

from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.dumps import DUMP_DEFAULT_THREAD_COUNT, SCHEMA_VERSION_CORE
from listenbrainz.dumps.exceptions import SchemaMismatchException
from listenbrainz.dumps.models import DumpTablesCollection
from listenbrainz.dumps.tables import PRIVATE_TABLES, PRIVATE_TABLES_TIMESCALE, PUBLIC_TABLES_IMPORT, \
    PUBLIC_TABLES_TIMESCALE_DUMP


def _import_dump(archive_path, db_engine: sqlalchemy.engine.Engine,
                 tables_collection: DumpTablesCollection, schema_version: int, threads=DUMP_DEFAULT_THREAD_COUNT):
    """ Import dump present in passed archive path into postgres db.

        Arguments:
            archive_path: path to the .tar.zst archive to be imported
            db_engine: an sqlalchemy Engine instance for making a connection
            tables_collection: dict of tables present in the archive with table name as key and
                    columns to import as values
            schema_version: the current schema version, to compare against the dumped file
            threads (int): the number of threads to use while decompressing, defaults to
                            db.DUMP_DEFAULT_THREAD_COUNT
    """
    file_table_mapping = {
        t.filename: t for t in tables_collection.tables
    }

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
                    if file_name in file_table_mapping:
                        current_app.logger.info('Importing data from %s...', file_name)
                        try:
                            table = file_table_mapping[file_name]
                            table._import(cursor, tar.extractfile(member))
                            connection.commit()
                        except Exception:
                            current_app.logger.critical('Exception while importing %s: ', file_name,
                                                        exc_info=True)
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
        _import_dump(private_dump_archive_path, db.engine, PRIVATE_TABLES, SCHEMA_VERSION_CORE, threads)
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
            tables_to_import.tables = [
                t for t in tables_to_import.tables
                if t.table_name != Identifier("user")
            ]

        _import_dump(public_dump_archive_path, db.engine, tables_to_import, SCHEMA_VERSION_CORE, threads)
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
