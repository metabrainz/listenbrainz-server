from __future__ import print_function
import db
import webserver
from werkzeug.serving import run_simple
import subprocess
import os
import click
import subprocess
import config
from urlparse import urlsplit


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
    webserver.schedule_jobs(application)
    run_simple(
        hostname=host,
        port=port,
        application=application,
        use_debugger=debug,
        use_reloader=debug,
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

    print('Create influx database...')
    subprocess.call(os.path.join(ADMIN_INFLUX_DIR, 'create_db.py'))
    print("Done!")


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


if __name__ == '__main__':
    cli()
