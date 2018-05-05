import click
import json
import os
import subprocess

from datetime import datetime
from googleapiclient.errors import HttpError
from influxdb import InfluxDBClient
from listenbrainz import config
from listenbrainz import db
from listenbrainz import stats
from listenbrainz import webserver
from listenbrainz.bigquery import create_bigquery_object
from urllib.parse import urlsplit
from werkzeug.serving import run_simple


cli = click.Group()

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')
MSB_ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../messybrainz', 'admin', 'sql')
ADMIN_INFLUX_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'influx')


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug=False):
    application = webserver.create_app()
    run_simple(
        hostname=host,
        port=port,
        application=application,
        use_debugger=debug,
        use_reloader=debug,
        processes=5
    )


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def run_api_compat_server(host, port, debug=False):
    application = webserver.create_api_compat_app()
    run_simple(
        hostname=host,
        port=port,
        application=application,
        use_debugger=debug,
        use_reloader=debug,
        processes=5
    )


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.option("--create-db", is_flag=True, help="Create the database and user.")
def init_db(force, create_db):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """

    db.init_db_connection(config.POSTGRES_ADMIN_URI)
    if force:
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'))
        if not res:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % res)

    if create_db:
        print('Creating user and a database...')
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_db.sql'))
        if not res:
            raise Exception('Failed to create new database and user! Exit code: %i' % res)

        print('Creating database extensions...')
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))
    # Don't raise an exception if the extension already exists

    application = webserver.create_app()
    with application.app_context():
        print('Creating schema...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_schema.sql'))

        print('Creating tables...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

        print('Creating primary and foreign keys...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

        print('Creating indexes...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_test_db(force=False):
    """Same as `init_db` command, but creates a database that will be used to
    run tests and doesn't import data (no need to do that).

    the `PG_CONNECT_TEST` variable must be defined in the config file.
    """

    db.init_db_connection(config.POSTGRES_ADMIN_URI)
    if force:
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'drop_test_db.sql'))
        if not res:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % res)

    print('Creating user and a database for testing...')
    res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_test_db.sql'))
    if not res:
        raise Exception('Failed to create test user and database! Exit code: %i' % res)

    res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))
    # Don't raise an exception if the extension already exists
    db.engine.dispose()

    print("Done!")


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.option("--create-db", is_flag=True, help="Skip creating database and user. Tables/indexes only.")
def init_msb_db(force, create_db):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """

    db.init_db_connection(config.POSTGRES_ADMIN_URI)
    if force:
        res = db.run_sql_script_without_transaction(os.path.join(MSB_ADMIN_SQL_DIR, 'drop_db.sql'))
        if not res:
            raise Exception('Failed to drop existing database and user! Exit code: %s' % res)

    if create_db:
        print('Creating user and a database...')
        res = db.run_sql_script_without_transaction(os.path.join(MSB_ADMIN_SQL_DIR, 'create_db.sql'))
        if not res:
            raise Exception('Failed to create new database and user! Exit code: %s' % res)

    print('Creating database extensions...')
    res = db.run_sql_script_without_transaction(os.path.join(MSB_ADMIN_SQL_DIR, 'create_extensions.sql'))
    # Don't raise an exception if the extension already exists

    db.engine.dispose()

#    print('Creating schema...')
#    exit_code = run_psql_script('create_schema.sql')
#    if exit_code != 0:
#        raise Exception('Failed to create database schema! Exit code: %i' % exit_code)

    db.init_db_connection(config.MESSYBRAINZ_SQLALCHEMY_DATABASE_URI)
    print('Creating tables...')
    db.run_sql_script(os.path.join(MSB_ADMIN_SQL_DIR, 'create_tables.sql'))

    print('Creating primary and foreign keys...')
    db.run_sql_script(os.path.join(MSB_ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(MSB_ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

    print('Creating indexes...')
    db.run_sql_script(os.path.join(MSB_ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
def init_influx():
    """ Initializes influx database. """

    print("Connecting to Influx...")
    influx_client = InfluxDBClient(
        host=config.INFLUX_HOST,
        port=config.INFLUX_PORT,
        database=config.INFLUX_DB_NAME,
    )
    print("Connected to Influx!")

    print("Creating influx database...")
    influx_client.create_database(config.INFLUX_DB_NAME)
    influx_client.create_retention_policy("one_week", "1w", 1, "listenbrainz")

    print("Done!")


def _load_fields():
    """ Returns the fields in the ListenBrainz Google BigQuery schema
    """
    schema_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'bigquery')
    with open(os.path.join(schema_dir, 'listen-schema.json')) as f:
        return json.load(f)


def _create_table(bigquery, table_name, force=True):
    """ Create a table with specified name in Google BigQuery.
    """
    try:
        result = bigquery.tables().get(
            projectId=config.BIGQUERY_PROJECT_ID,
            datasetId=config.BIGQUERY_DATASET_ID,
            tableId=table_name,
        ).execute(num_retries=5)
        if 'creationTime' in result:
            print('Table %s already present in BigQuery...' % table_name)
            if force:
                print('Deleting table...')
                bigquery.tables().delete(
                    projectId=config.BIGQUERY_PROJECT_ID,
                    datasetId=config.BIGQUERY_DATASET_ID,
                    tableId=table_name,
                ).execute(num_retries=5)
            else:
                return
    except HttpError as e:
        if e.resp.status != 404:
            print('Error while getting information for table %s...' % table_name)
            raise

    creation_request_body = {
        'tableReference': {
            'projectId': config.BIGQUERY_PROJECT_ID,
            'datasetId': config.BIGQUERY_DATASET_ID,
            'tableId': table_name,
        },
        'schema': {
            'fields': _load_fields()
        },
    }

    response = bigquery.tables().insert(
        projectId=config.BIGQUERY_PROJECT_ID,
        datasetId=config.BIGQUERY_DATASET_ID,
        body=creation_request_body,
    ).execute(num_retries=5)
    print('Table %s created!' % table_name)


@cli.command()
@click.option("-f", "--force", is_flag=True, help="Drop existing tables in BigQuery")
def init_bigquery(force):
    """ Initializes BigQuery dataset and creates required tables.
    """
    bigquery = create_bigquery_object()
    _create_table(bigquery, 'before_2002', force=force) # extra table for listens before Last.FM (should be bad data)
    for year in range(2002, datetime.today().year + 1):
        _create_table(bigquery, str(year), force=force)


# Add other commands here
import listenbrainz.stats.populate as populate
cli.add_command(populate.cli, name="stats")
import listenbrainz.db.dump_manager as dump_manager
cli.add_command(dump_manager.cli, name="dump")


if __name__ == '__main__':
    cli()
