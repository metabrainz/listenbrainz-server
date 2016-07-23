from __future__ import print_function
import db
import webserver
from werkzeug.serving import run_simple
import subprocess
import os
import click
import config
from urlparse import urlsplit


application = webserver.create_app()

cli = click.Group()

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'admin', 'sql')
MSB_ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../messybrainz-server', 'admin', 'sql')


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=8080, show_default=True)
@click.option("--debug", "-d", is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides "
                   "'DEBUG' value in the config file.")
def runserver(host, port, debug=False):
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
@click.option("-create-db", is_flag=True, help="Skip creating database and user. Tables/indexes only.")
def init_db(force, create_db):
    """Initializes database.

    This process involves several steps:
    1. Table structure is created.
    2. Primary keys and foreign keys are created.
    3. Indexes are created.
    """

    uri = urlsplit(application.config['SQLALCHEMY_DATABASE_URI'])
    if force:
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER +
                                    ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                    os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    if create_db:
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

    with application.app_context():
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

    uri = urlsplit(application.config['TEST_SQLALCHEMY_DATABASE_URI'])
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
    uri = urlsplit(application.config['MESSYBRAINZ_SQLALCHEMY_DATABASE_URI'])

    def run_psql_script(script, superuser=False):
        if superuser:
            username = config.PG_SUPER_USER
        else:
            username = uri.username
        return subprocess.call(
            'psql -U ' + username + ' -d messybrainz ' +
            '-h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
            os.path.join(MSB_ADMIN_SQL_DIR, script),
            shell=True,
        )

    if force:
        exit_code = run_psql_script('drop_db.sql', superuser=True)
        if exit_code != 0:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    if create_db:
        print('Creating user and a database...')
        exit_code = subprocess.call('psql -U ' + config.PG_SUPER_USER +
                                    ' -h ' + uri.hostname + ' -p ' + str(uri.port) + ' < ' +
                                    os.path.join(MSB_ADMIN_SQL_DIR, 'create_db.sql'),
                                    shell=True)
        if exit_code != 0:
            raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    print('Creating database extensions...')
    exit_code = run_psql_script('create_extensions.sql', superuser=True)
    if exit_code != 0:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    print('Creating tables...')
    exit_code = run_psql_script('create_tables.sql')
    if exit_code != 0:
        raise Exception('Failed to create database tables! Exit code: %i' % exit_code)

    print('Creating primary and foreign keys...')
    exit_code = run_psql_script('create_primary_keys.sql')
    if exit_code != 0:
        raise Exception('Failed to create primary keys! Exit code: %i' % exit_code)
    exit_code = run_psql_script('create_foreign_keys.sql')
    if exit_code != 0:
        raise Exception('Failed to create foreign keys! Exit code: %i' % exit_code)

    print('Creating indexes...')
    exit_code = run_psql_script('create_indexes.sql')
    if exit_code != 0:
        raise Exception('Failed to create indexes keys! Exit code: %i' % exit_code)

    print("Done!")


if __name__ == '__main__':
    cli()
