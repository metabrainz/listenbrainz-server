from messybrainz import db
from messybrainz.db.artist import truncate_recording_artist_join,\
                                fetch_and_store_artist_mbids_for_all_recording_mbids,\
                                create_artist_credit_clusters,\
                                truncate_artist_credit_cluster_and_redirect_tables
from messybrainz.db import artist
from messybrainz.db import release
from messybrainz.webserver import create_app
from brainzutils import musicbrainz_db
from sqlalchemy import text

import subprocess
import os
import click
import logging

import messybrainz.default_config as config
try:
    import messybraiz.custom_config as config
except ImportError:
    pass
from messybrainz.db.recording import create_recording_clusters,\
                                    truncate_recording_cluster_and_recording_redirect_table


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
        exit_code = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'drop_db.sql'))
        if not exit_code:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating user and a database...')
    exit_code = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_db.sql'))
    if not exit_code:
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

        print('Creating functions...')
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_functions.sql'))

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
        if not exit_code:
            raise Exception('Failed to drop existing database and user! Exit code: %i' % exit_code)

    print('Creating database and user for testing...')
    exit_code = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_test_db.sql'))
    if not exit_code:
        raise Exception('Failed to create new database and user! Exit code: %i' % exit_code)

    exit_code = db.run_sql_script_without_transaction(os.path.join(ADMIN_SQL_DIR, 'create_extensions.sql'))
    if not exit_code:
        raise Exception('Failed to create database extensions! Exit code: %i' % exit_code)

    db.init_db_engine(config.TEST_SQLALCHEMY_DATABASE_URI)

    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_functions.sql'))
    db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))


    print("Done!")


@cli.command()
def create_recording_clusters_for_mbids():
    """Creates clusters for recording using recording MBIDs present in 
       recording_json table.
    """
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        clusters_modified, clusters_add_to_redirect = create_recording_clusters()
        print("Clusters modified: {0}.".format(clusters_modified))
        print("Clusters add to redirect table: {0}.".format(clusters_add_to_redirect))
        print ("Done!")
    except Exception as error:
        print("While creating recording clusters. An error occured: {0}".format(error))
        raise


@cli.command()
def truncate_recording_cluster_and_redirect():
    """Truncate recording_cluster and recording_redirect tables."""
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        truncate_recording_cluster_and_recording_redirect_table()
        print("recording_cluster and recording_redirect table truncated.")
    except Exception as error:
        print("An error occured while truncating recording_cluster and recording_redirect: {0}".format(error))
        raise


@cli.command()
def fetch_and_store_artist_mbids():
    """ Fetches artist MBIDs from the musicbrainz database for the recording MBIDs
        in the recording_json table submitted while submitting a listen. It fetches
        only the artist MBIDs for the recordings MBIDs which are not in recording_artist_join
        table. In the end it prints to the console the total recording MBIDs it processed
        and the total recording MBIDs it added to the recording_artist_join table.
    """

    # Init databases
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    musicbrainz_db.init_db_engine(config.MB_DATABASE_URI)

    try:
        num_recording_mbids_processed, num_recording_mbids_added = fetch_and_store_artist_mbids_for_all_recording_mbids()
        print("Total recording MBIDs processed: {0}.".format(num_recording_mbids_processed))
        print("Total recording MBIDs added to table: {0}.".format(num_recording_mbids_added))
        print("Done!")
    except Exception as error:
        print("Unable to fetch artist MBIDs. An error occured: {0}".format(error))
        raise


@cli.command()
def truncate_recording_artist_join_table():
    """Truncate table recording_artist_join."""
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        truncate_recording_artist_join()
        print("Table recording_artist_join truncated.")
    except Exception as error:
        print("An error occured while truncating tables: {0}".format(error))
        raise


@cli.command()
@click.option("--verbose", "-v", default='WARNING', help="Print debug information for given verbose level(WARNING, INFO, DEBUG).")
def create_artist_credit_clusters_for_mbids(verbose='WARNING'):
    """Creates clusters for artist_credits using artist MBIDs present in
       recording_json table.
    """

    try:
        if verbose == 'INFO':
            logging.basicConfig(format='%(message)s', level=logging.INFO)
        elif verbose == 'DEBUG':
            logging.basicConfig(format='%(message)s', level=logging.DEBUG)
        else:
            print("Invalid logging level specified. Using default logging level(WARNING).")

        print("Creating artist_credit clusters...")

        db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
        logging.debug("=" * 80)
        clusters_modified, clusters_add_to_redirect = create_artist_credit_clusters()
        logging.debug("=" * 80)
        print("Clusters modified: {0}.".format(clusters_modified))
        print("Clusters add to redirect table: {0}.".format(clusters_add_to_redirect))
        print("Done!")
    except Exception as error:
        print("While creating artist_credit clusters. An error occured: {0}".format(error))
        raise


@cli.command()
@click.option("--verbose", "-v", default=0, help="Print debug information for given verbose level(0,1,2).")
def create_release_clusters_for_mbids(verbose=0):
    """Creates clusters for release using release MBIDs present in
       recording_json table.
    """

    if verbose == 1:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    elif verbose == 2:
        logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    print("Creating release clusters...")

    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        logging.info("=" * 80)
        clusters_modified, clusters_add_to_redirect = release.create_release_clusters()
        logging.info("=" * 80)
        print("Clusters modified: {0}.".format(clusters_modified))
        print("Clusters add to redirect table: {0}.".format(clusters_add_to_redirect))
        print ("Done!")
    except Exception as error:
        print("While creating release clusters. An error occured: {0}".format(error))
        raise


@cli.command()
def truncate_artist_credit_cluster_and_redirect():
    """Truncate artist_credit_cluster and artist_credit_redirect table."""

    logging.basicConfig(format='%(message)s', level=logging.INFO)
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        truncate_artist_credit_cluster_and_redirect_tables()
        logging.info("artist_credit_cluster and artist_credit_redirect table truncated.")

    except Exception as error:
        logging.error("An error occured while truncating artist_credit_cluster"
            "and artist_credit_redirect table: {0}".format(error)
        )
        raise


@cli.command()
def truncate_release_cluster_and_redirect():
    """Truncate release_cluster and release_redirect tables."""
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        release.truncate_release_cluster_and_release_redirect_table()
        print("release_cluster and release_redirect table truncated.")
    except Exception as error:
        print("An error occured while truncating release_cluster and release_redirect: {0}".format(error))
        raise


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Print debug information.")
def fetch_and_store_releases(verbose=False):
    """ Fetches releases from the musicbrainz database for the recording MBIDs
        in the recording_json table submitted while submitting a listen. It fetches
        only the releases for the recordings MBIDs which are not in recording_release_join
        table. In the end it prints to the console the total recording MBIDs it processed
        and the total recording MBIDs it added to the recording_release_join table.
    """

    print("Fetching release for recording MBIDs...")
    if verbose:
        logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    # Init databases
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    musicbrainz_db.init_db_engine(config.MB_DATABASE_URI)

    try:
        logging.debug("=" * 80)
        num_recording_mbids_processed, num_recording_mbids_added = release.fetch_and_store_releases_for_all_recording_mbids()
        logging.debug("=" * 80)
        print("Total recording MBIDs processed: {0}.".format(num_recording_mbids_processed))
        print("Total recording MBIDs added to table: {0}.".format(num_recording_mbids_added))
        print("Done!")
    except Exception as error:
        print("Unable to fetch releases. An error occured: {0}".format(error))
        raise


@cli.command()
def truncate_recording_release_join_table():
    """Truncate table recording_release_join."""
    db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        release.truncate_recording_release_join()
        print("Table recording_release_join truncated.")
    except Exception as error:
        print("An error occured while truncating recording_release_join table: {0}".format(error))
        raise


@cli.command()
@click.option("--verbose", "-v", default="WARNING", help="Print debug information for given verbose level(WARNING, INFO, DEBUG).")
def create_clusters_using_fetched_artist_mbids(verbose="WARNING"):
    """Creates clusters for artist_credits using artist MBIDs fetched from MusicBrainz
       database and stored in recording_artist_join table.
    """

    try:
        if verbose == "INFO":
            logging.basicConfig(format='%(message)s', level=logging.INFO)
        elif verbose == "DEBUG":
            logging.basicConfig(format='%(message)s', level=logging.DEBUG)
        elif verbose != "WARNING":
            print("Invalid logging level specified. Using default logging level(WARNING).")

        print("Creating artist_credit clusters...")
        db.init_db_engine(config.SQLALCHEMY_DATABASE_URI)

        logging.debug("=" * 80)
        clusters_modified, clusters_add_to_redirect = artist.create_clusters_using_fetched_artist_mbids()
        logging.debug("=" * 80)
        print("Clusters modified: {0}.".format(clusters_modified))
        print("Clusters add to redirect table: {0}.".format(clusters_add_to_redirect))
        print("Done!")
    except Exception as error:
        print("While creating artist_credit clusters using fetched artist MBIDs. An error occured: {0}".format(error))


if __name__ == '__main__':
    cli()
