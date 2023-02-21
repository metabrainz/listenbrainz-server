#!/usr/bin/env python3

import sys
import os
import subprocess

import click

from mapping.canonical_musicbrainz_data import create_canonical_musicbrainz_data
from mapping.typesense_index import build_all as action_build_index
from mapping.mapping_test.mapping_test import test_mapping as action_test_mapping
from mapping.utils import log, CRON_LOG_FILE
from mapping.release_colors import sync_release_color_table, incremental_update_release_color_table
from reports.tracks_of_the_year import calculate_tracks_of_the_year
from reports.top_discoveries import calculate_top_discoveries
from mapping.mb_metadata_cache import create_mb_metadata_cache, incremental_update_mb_metadata_cache, \
    cleanup_mbid_mapping_table
from mapping.spotify_metadata_index import create_spotify_metadata_index


@click.group()
def cli():
    pass


@cli.command()
def create_all():
    """
        Create all canonical data in one go. First mb canonical data, then its typesense index.
    """
    create_canonical_musicbrainz_data(True)
    action_build_index()


@cli.command()
@click.option("--use-lb-conn/--use-mb-conn", default=True, help="whether to create the tables in LB or MB")
def canonical_data(use_lb_conn):
    """
        Create the MBID Mapping tables. (mbid_mapping, mbid_mapping_release, canonical_recording, recording_canonical_release)
    """
    create_canonical_musicbrainz_data(use_lb_conn)


@cli.command()
def test_mapping():
    """
        Test the created mbid mapping. The MBID mapping must have been created before running this.
    """
    action_test_mapping()


@cli.command()
def build_index():
    """
        Build the typesense index of the mbid mapping. The mbid mapping must be run first in order to build this index.
    """
    action_build_index()


@cli.command()
def sync_coverart():
    """
        Force a re-sync of the release_color table, in case it has gone out of sync.
    """
    sync_release_color_table()


@cli.command()
def update_coverart():
    """
        Update the release_color table incrementally. Designed to be called hourly by cron.
    """
    incremental_update_release_color_table()


@cli.command()
def cron_log():
    """
        Print the internal cron log file for debugging purposes.
    """
    if os.path.exists(CRON_LOG_FILE):
        log("Current cron job log file:")
        subprocess.run(["cat", CRON_LOG_FILE])
    else:
        log("Log file is empty")


@cli.command()
@click.argument('year', type=int)
def top_discoveries(year):
    """
        Top discoveries for year -- this creates a table in the mapping schema of the provided mb-docker database
        that lists all the tracks that a user listened to the first time in the given year.
    """
    calculate_top_discoveries(year)


@cli.command()
@click.argument('year', type=int)
def top_tracks(year):
    """
        Tracks for the year -- this also creates a table in the mapping schema, where this one creates a historgram
        of which tracks and how many times a user played for a given year.
    """
    calculate_tracks_of_the_year(year)


@cli.command()
@click.option("--use-lb-conn/--use-mb-conn", default=True, help="whether to create the tables in LB or MB")
def build_mb_metadata_cache(use_lb_conn):
    """
        Build the MB metadata cache that LB uses
    """
    create_mb_metadata_cache(use_lb_conn)


@cli.command()
@click.option("--use-lb-conn/--use-mb-conn", default=True, help="whether to create the tables in LB or MB")
def update_mb_metadata_cache(use_lb_conn):
    """
        Update the MB metadata cache that LB uses incrementally.
    """
    incremental_update_mb_metadata_cache(use_lb_conn)


@cli.command()
def cron_build_mb_metadata_cache():
    """ Build the mb metadata cache and tables it depends on in production in appropriate databases.
     After building the cache, cleanup mbid_mapping table.
    """
    create_canonical_musicbrainz_data(False)
    create_mb_metadata_cache(True)
    cleanup_mbid_mapping_table()


@cli.command()
@click.option("--use-lb-conn/--use-mb-conn", default=True, help="whether to create the tables in LB or MB")
def build_spotify_metadata_index(use_lb_conn):
    """
        Build the spotify metadata index that LB uses
    """
    create_spotify_metadata_index(use_lb_conn)


def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == "__main__":
    cli()
    sys.exit(0)
