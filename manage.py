from listenbrainz import db
from listenbrainz import webserver
from listenbrainz import stats
from werkzeug.serving import run_simple
import subprocess
import os
import click
import subprocess
from urllib.parse import urlsplit
from influxdb import InfluxDBClient

from listenbrainz.utils import safely_import_config
safely_import_config()


@click.group()
def cli():
    pass

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


@cli.command(name="run_api_compat_server")
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

@cli.command(name="run_follow_server")
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8081, show_default=True)
@click.option("--debug", "-d", is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def run_follow_server(host, port, debug=True):
    from listenbrainz.follow_server.follow_server import run_follow_server
    run_follow_server(host=host, port=port, debug=debug)


@cli.command(name="init_db")
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.option("--create-db", is_flag=True, help="Create the database and user.")
def init_db(force, create_db):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """
    from listenbrainz import config
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

        db.init_db_connection(config.POSTGRES_ADMIN_LB_URI)
        print('Creating database extensions...')
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))
    # Don't raise an exception if the extension already exists

    application = webserver.create_app()
    with application.app_context():
        print('Creating schema...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_schema.sql'))

        print('Creating Types...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))

        print('Creating tables...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

        print('Creating primary and foreign keys...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

        print('Creating indexes...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

        print("Done!")


@cli.command(name="init_msb_db")
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.option("--create-db", is_flag=True, help="Skip creating database and user. Tables/indexes only.")
def init_msb_db(force, create_db):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """
    from listenbrainz import config
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

    print('Creating functions...')
    db.run_sql_script(os.path.join(MSB_ADMIN_SQL_DIR, 'create_functions.sql'))

    print('Creating indexes...')
    db.run_sql_script(os.path.join(MSB_ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command(name="init_influx")
def init_influx():
    """ Initializes influx database. """
    from listenbrainz import config
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


# Add other commands here
import listenbrainz.spark.request_manage as spark_request_manage
cli.add_command(spark_request_manage.cli, name="spark")
import listenbrainz.db.dump_manager as dump_manager
cli.add_command(dump_manager.cli, name="dump")
import listenbrainz.listen_replay.cli as listen_replay
cli.add_command(listen_replay.cli, name="replay")


if __name__ == '__main__':
    cli()
