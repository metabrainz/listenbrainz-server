from messybrainz import db
from webserver import create_app
import subprocess
import os
import click

import default_config as config
try:
    import custom_config as config
except ImportError:
    pass

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')

cli = click.Group()


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug=False):
    create_app(debug=debug).run(host=host, port=port)


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
def init_db(force):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """
    db.init_db_engine(config.POSTGRES_ADMIN_URI)
    if force:
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'))
        if not res:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating user and a database...')
    res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_db.sql'))
    if not res:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    print('Creating database extensions...')
    exit_code = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))

    app = create_app()
    with app.app_context():
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

    `TEST_SQLALCHEMY_DATABASE_URI` variable must be defined in the config file.
    """
    db.init_db_engine(config.POSTGRES_ADMIN_URI)
    if force:
        exit_code = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'drop_test_db.sql'))
        if not res:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating database and user for testing...')
    exit_code = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_test_db.sql'))
    if not res:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    exit_code = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))
    if not res:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_engine(config.TEST_SQLALCHEMY_DATABASE_URI)

    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")


if __name__ == '__main__':
    cli()
