from __future__ import print_function
import db
from webserver import create_app
import subprocess
import os
import click
import config

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = click.Group()


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", type=bool,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug):
    create_app().run(host=host, port=port, debug=debug)


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_db(force):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """
    if force:
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER + ' < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating user and a database...')
    exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER + ' < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_db.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    print('Creating database extensions...')
    exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER + ' -d messybrainz < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_connection(config.PG_CONNECT)

    print('Creating tables...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))

    print('Creating primary and foreign keys...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

    print('Creating indexes...')
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_test_db(force=False):
    """Same as `init_db` command, but creates a database that will be used to run tests.

    `PG_CONNECT_TEST` variable must be defined in the config file.
    """
    if force:
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER + ' < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'drop_test_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating database and user for testing...')
    exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER + ' < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_test_db.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER + ' -d myb_test < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_connection(config.PG_CONNECT_TEST)

    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


if __name__ == '__main__':
    cli()
