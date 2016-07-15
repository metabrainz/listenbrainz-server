from __future__ import print_function
import db
from webserver import create_app, schedule_jobs
from werkzeug.wsgi import DispatcherMiddleware
import subprocess
import os
import click
import config
from urlparse import urlsplit

application = DispatcherMiddleware(create_app())

cli = click.Group()

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')
MSB_ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../messybrainz-server', 'admin', 'sql')

@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", type=bool,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug):
    app = create_app()
    schedule_jobs(app)
    app.run(host=host, port=port, debug=debug)


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.option("--skip-create", "-s", is_flag=True, help="Skip creating database and user. Tables/indexes only.")
def init_db(force, skip_create):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """

    uri = urlsplit(create_app().config['SQLALCHEMY_DATABASE_URI'])
    if force:
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER +
                                    ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)


    if not skip_create:
        print('Creating user and a database...')
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER +
                                    ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'create_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

        print('Creating database extensions...')
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER + ' -d listenbrainz ' +
                                    '-h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    with create_app().app_context():
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
    """Same as `init_db` command, but creates a database that will be used to
    run tests and doesn't import data (no need to do that).

    `PG_CONNECT_TEST` variable must be defined in the config file.
    """

    uri = urlsplit(create_app().config['TEST_SQLALCHEMY_DATABASE_URI'])
    if force:
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER +
                                    ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'drop_test_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating database and user for testing...')
    exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER +
                                ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_test_db.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER + ' -d lb_test ' +
                                ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'),
                                shell=True)
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_connection(config.TEST_SQLALCHEMY_DATABASE_URI)

    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    print("Done!")

def run_script(uri, script):
    return subprocess.call('psql -U ' + uri.username + ' -d messybrainz ' +
                           '-h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                           os.path.join(MSB_ADMIN_SQL_DIR, script),
                           shell=True)

@cli.command()
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.option("--skip-create", "-s", is_flag=True, help="Skip creating database and user. Tables/indexes only.")
def init_msb_db(force, skip_create):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """

    uri = urlsplit(create_app().config['MESSYBRAINZ_SQLALCHEMY_DATABASE_URI'])
    if force:
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER +
                                    ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                    os.path.join(MSB_ADMIN_SQL_DIR, 'drop_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)


    if not skip_create:
        print('Creating user and a database...')
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER +
                                    ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                    os.path.join(MSB_ADMIN_SQL_DIR, 'create_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    print('Creating database extensions...')
    exit_code = run_script(uri, 'create_extensions.sql')
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    print('Creating tables...')
    exit_code = run_script(uri, 'create_tables.sql')
    if exit_code != 0:
        raise Exception('Failed to create database tables! Exit code: %i' % exit_code)

    print('Creating primary and foreign keys...')
    exit_code = run_script(uri, 'create_primary_keys.sql')
    if exit_code != 0:
        raise Exception('Failed to create primary keys! Exit code: %i' % exit_code)
    exit_code = run_script(uri, 'create_foreign_keys.sql')
    if exit_code != 0:
        raise Exception('Failed to create foreign keys! Exit code: %i' % exit_code)

    print('Creating indexes...')
    exit_code = run_script(uri, 'create_indexes.sql')
    if exit_code != 0:
        raise Exception('Failed to create indexes keys! Exit code: %i' % exit_code)

    print("Done!")

if __name__ == '__main__':
    cli()
