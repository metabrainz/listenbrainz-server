import os
from datetime import date
from time import sleep

import click
import sqlalchemy

from listenbrainz import db
from listenbrainz import webserver
from listenbrainz.background import export
from listenbrainz.db import timescale as ts, do_not_recommend

from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data as ts_recalculate_all_user_data, \
    update_user_listen_data as ts_update_user_listen_data, \
    add_missing_to_listen_users_metadata as ts_add_missing_to_listen_users_metadata,\
    delete_listens as ts_delete_listens, \
    refresh_top_manual_mappings as ts_refresh_top_manual_mappings
from listenbrainz.messybrainz import update_msids_from_mapping
from listenbrainz.metadata_cache.seeder import submit_new_releases_to_cache
from listenbrainz.troi.daily_jams import run_daily_jams_troi_bot
from listenbrainz.webserver import create_app


@click.group()
def cli():
    pass


ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')
TIMESCALE_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'timescale')


@cli.command(name="run_websockets")
@click.option("--host", "-h", default="0.0.0.0", show_default=True)
@click.option("--port", "-p", default=7082, show_default=True)
@click.option("--debug",
              "-d",
              is_flag=True,
              help="Turns debugging mode on or off. If specified, overrides "
              "'DEBUG' value in the config file.")
def run_websockets(host, port, debug=True):
    from listenbrainz.websockets.websockets import run_websockets
    application = webserver.create_app()
    with application.app_context():
        run_websockets(application, host=host, port=port, debug=debug)


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
    if "PYTHON_TESTS_RUNNING" in os.environ:
        db_connect = db.create_test_database_connect_strings()
        db.init_db_connection(db_connect["DB_CONNECT_ADMIN"])
        config.PYTHON_TESTS_RUNNING = True
    else:
        db_connect = {"DB_NAME": "listenbrainz", "DB_USER": "listenbrainz"}
        db.init_db_connection(config.POSTGRES_ADMIN_URI)
    if force:
        res = db.run_sql_query_without_transaction(
            [f"DROP DATABASE IF EXISTS {db_connect['DB_NAME']}", f"DROP USER IF EXISTS {db_connect['DB_USER']}"])
        if not res:
            raise Exception('Failed to drop existing database/user! Exit code: %i' % res)

    if create_db or force:
        print('PG: Creating user and a database...')

        if "PYTHON_TESTS_RUNNING" in os.environ:
            res = db.run_sql_query_without_transaction([
                f"CREATE USER {db_connect['DB_USER']} NOCREATEDB NOSUPERUSER",
                f"ALTER USER {db_connect['DB_USER']} WITH PASSWORD 'listenbrainz'",
                f"CREATE DATABASE {db_connect['DB_NAME']} WITH OWNER = {db_connect['DB_USER']} TEMPLATE template0 ENCODING = 'UNICODE'"
            ])
        else:
            res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_db.sql'))
        if not res:
            raise Exception('Failed to create new database and user! Exit code: %i' % res)

        if "PYTHON_TESTS_RUNNING" in os.environ:
            db.init_db_connection(db_connect["DB_CONNECT_ADMIN_LB"])
        else:
            db.init_db_connection(config.POSTGRES_ADMIN_LB_URI)

        print('PG: Creating database extensions...')
        # Don't raise an exception if the extension already exists
        res = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))

        res = db.run_sql_query_without_transaction(
            [f"ALTER DATABASE {db_connect['DB_NAME']} SET pg_trgm.word_similarity_threshold = 0.1"])
        if not res:
            raise Exception('Failed to create to set pg_trgm.word_similarity_threshold! Exit code: %i' % res)

    application = webserver.create_app()
    with application.app_context():
        print('PG: Creating schema...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_schema.sql'))

        print('PG: Creating Types...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_types.sql'))

        print('PG: Creating tables...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        res = db.run_sql_query_without_transaction(
            [f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {db_connect['DB_NAME']}"])
        if not res:
            raise Exception('Failed to set table priviledges! Exit code: %i' % res)

        print('PG: Creating primary and foreign keys...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))

        print('PG: Creating indexes...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

        print("Done!")


@cli.command(name="init_ts_db")
@click.option("--force", "-f", is_flag=True, help="Drop existing database and user.")
@click.option("--create-db", is_flag=True, help="Create the database and user.")
def init_ts_db(force, create_db):
    """Initializes database.

    This process involves several steps:
        1. Table structure is created.
        2. Indexes are created.
        3. Views are created
    """
    from listenbrainz import config
    if "PYTHON_TESTS_RUNNING" in os.environ:
        ts_connect = ts.create_test_timescale_connect_strings()
        ts.init_db_connection(ts_connect["DB_CONNECT_ADMIN"])
        config.PYTHON_TESTS_RUNNING = True
    else:
        ts_connect = {"DB_NAME": "listenbrainz_ts", "DB_USER": "listenbrainz_ts"}
        ts.init_db_connection(config.TIMESCALE_ADMIN_URI)
    if force:
        res = ts.run_sql_query_without_transaction(
            [f"DROP DATABASE IF EXISTS {ts_connect['DB_NAME']}", f"DROP USER IF EXISTS {ts_connect['DB_USER']}"])
        if not res:
            raise Exception('Failed to drop existing database/user! Exit code: %i' % res)

    if create_db or force:
        print('TS: Creating user and a database...')
        retries = 0
        while True:
            try:
                if "PYTHON_TESTS_RUNNING" in os.environ:
                    res = ts.run_sql_query_without_transaction([
                        f"CREATE USER {ts_connect['DB_USER']} NOCREATEDB NOSUPERUSER",
                        f"ALTER USER {ts_connect['DB_USER']} WITH PASSWORD 'listenbrainz_ts'",
                        f"CREATE DATABASE {ts_connect['DB_NAME']} WITH OWNER = {ts_connect['DB_USER']} TEMPLATE template0 ENCODING = 'UNICODE'"
                    ])
                else:
                    res = ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_db.sql'))
                break
            except sqlalchemy.exc.OperationalError:
                print("Trapped template1 access error, FFS! Sleeping, trying again.")
                retries += 1
                if retries == 5:
                    raise
                sleep(1)
                continue

        if not res:
            raise Exception('Failed to create new database and user! Exit code: %i' % res)

        if "PYTHON_TESTS_RUNNING" in os.environ:
            ts.init_db_connection(ts_connect["DB_CONNECT_ADMIN_LB"])
        else:
            ts.init_db_connection(config.TIMESCALE_ADMIN_LB_URI)

        print('TS: Creating database extensions...')
        res = ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_extensions.sql'))
        # Don't raise an exception if the extension already exists
        # TODO fix this
        if not res:
            raise Exception('Failed to create ts extension! Exit code: %i' % res)

        res = ts.run_sql_query_without_transaction(
            [f"ALTER DATABASE {ts_connect['DB_NAME']} SET pg_trgm.word_similarity_threshold = 0.1"])
        if not res:
            raise Exception('Failed to create to set pg_trgm.word_similarity_threshold! Exit code: %i' % res)


    if "PYTHON_TESTS_RUNNING" in os.environ:
        ts.init_db_connection(ts_connect["DB_CONNECT"])
    else:
        ts.init_db_connection(config.SQLALCHEMY_TIMESCALE_URI)

    application = webserver.create_app()
    with application.app_context():
        print('TS: Creating Schemas...')
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_schemas.sql'))

        print('TS: Creating Types...')
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_types.sql'))

        print('TS: Creating tables...')
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_tables.sql'))

        print('TS: Insert default rows...')
        res = ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'insert_default_data.sql'))

        print('TS: Creating views...')
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_views.sql'))

        print('TS: Creating indexes...')
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_indexes.sql'))

        print('TS: Creating Primary and Foreign Keys...')
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_primary_keys.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_foreign_keys.sql'))

        print("Done!")


@cli.command(name="update_user_emails")
def update_user_emails():
    from listenbrainz.webserver.login import copy_files_from_mb_to_lb
    application = webserver.create_app()
    with application.app_context():
        copy_files_from_mb_to_lb.copy_emails()


@cli.command(name="set_rate_limits")
@click.argument("per_token_limit", type=click.IntRange(1, None))
@click.argument("per_ip_limit", type=click.IntRange(1, None))
@click.argument("window_size", type=click.IntRange(1, None))
def set_rate_limits(per_token_limit, per_ip_limit, window_size):
    from brainzutils.ratelimit import set_rate_limits
    application = webserver.create_app()
    with application.app_context():
        set_rate_limits(per_token_limit, per_ip_limit, window_size)


@cli.command(name="recalculate_all_user_data")
def recalculate_all_user_data():
    """ Recalculate all user timestamps and listen counts.

    .. note::
        **ONLY USE THIS WHEN YOU KNOW WHAT YOU ARE DOING!**
    """
    application = webserver.create_app()
    with application.app_context():
        ts_recalculate_all_user_data()


@cli.command(name="update_user_listen_data")
def update_user_listen_data():
    """ Scans listen table and update listen metadata for all users """
    application = webserver.create_app()
    with application.app_context():
        ts_update_user_listen_data()


@cli.command(name="delete_pending_listens")
def delete_pending_listens():
    """ Complete all pending listen deletes since last cron run """
    application = webserver.create_app()
    with application.app_context():
        ts_delete_listens()


@cli.command(name="delete_listens")
def complete_delete_listens():
    """ Complete all pending listen deletes and also run update script for
    updating listen metadata since last cron run """
    application = webserver.create_app()
    with application.app_context():
        ts_delete_listens()


@cli.command(name="add_missing_to_listen_users_metadata")
def add_missing_to_listen_users_metadata():
    application = webserver.create_app()
    with application.app_context():
        ts_add_missing_to_listen_users_metadata()


@cli.command()
@click.option("-u", "--user", type=str)
@click.option("-t", "--token", type=str)
@click.argument("releasembid", type=str)
def submit_release(user, token, releasembid):
    """Submit a release from MusicBrainz to the local ListenBrainz instance

    Specify -u to use the token of this user when submitting, or
    -t to specify a specific token.
    """
    if user is None and token is None:
        raise click.ClickException(f"Need --user or --token")
    if user is not None:
        import listenbrainz.db.user
        application = webserver.create_app()
        with application.app_context():
            user_ob = listenbrainz.db.user.get_by_mb_id(webserver.db_conn, user)
            if user_ob is None:
                raise click.ClickException(f"No such user: {user}")
            token = user_ob["auth_token"]
            print("token is", token)
    import listenbrainz.misc.submit_release
    listenbrainz.misc.submit_release.submit_release_impl(token, releasembid, "http://web:80")


@cli.command(name="notify_yim_users")
@click.option("--year", type=int, help="Year for which to send the emails", default=date.today().year)
def notify_yim_users(year: int):
    application = webserver.create_app()
    with application.app_context():
        from listenbrainz.db import year_in_music
        year_in_music.notify_yim_users(webserver.db_conn, webserver.ts_conn, year)


@cli.command()
@click.option("--create-all",
              is_flag=True,
              help="Create the daily jams for all users. if false (default), only for users according to timezone.")
def run_daily_jams(create_all):
    """ Generate daily playlists for users soon after the new day begins in their timezone. This is an internal LB
    method and not a core function of troi.
    """
    with create_app().app_context():
        run_daily_jams_troi_bot(webserver.db_conn, webserver.ts_conn, create_all)


@cli.command()
def run_metadata_cache_seeder():
    """ Query external services' new releases api for new releases and submit those to our cache as seeds """
    submit_new_releases_to_cache()


@cli.command()
def update_msid_tables():
    """ Scan tables using msids to find matching mbids from mapping tables and update them. """
    with create_app().app_context():
        update_msids_from_mapping.run_all_updates()


@cli.command()
def clear_expired_do_not_recommends():
    """ Delete expired do not recommend entries from database """
    app = create_app()
    with app.app_context():
        app.logger.info("Starting process to clean up expired do not recommends")
        do_not_recommend.clear_expired(webserver.db_conn)
        app.logger.info("Completed process to clean up expired do not recommends")


@cli.command()
def refresh_top_manual_mappings():
    """ Refresh top manual msid-mbid mappings view """
    app = create_app()
    with app.app_context():
        app.logger.info("Starting process to refresh top manual mappings")
        ts_refresh_top_manual_mappings()
        app.logger.info("Completed process to refresh top manual mappings")


@cli.command()
def delete_old_user_data_exports():
    """ Delete old and expired user data exports """
    app = create_app()
    with app.app_context():
        app.logger.info("Deleting old and expired user data exports")
        export.cleanup_old_exports(webserver.db_conn)
        app.logger.info("Completed deleting old and expired user data exports")
