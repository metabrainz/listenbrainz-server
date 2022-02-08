#!/usr/bin/env python3

import sys
import os
import subprocess

import click

from mapping.mbid_mapping import create_mbid_mapping
from mapping.typesense_index import build_index as action_build_index
from mapping.year_mapping import create_year_mapping
from mapping.mapping_test.mapping_test import test_mapping as action_test_mapping
from mapping.utils import log, CRON_LOG_FILE
from mapping.release_colors import sync_release_color_table, incremental_update_release_color_table
from reports.tracks_of_the_year import calculate_tracks_of_the_year
from reports.top_discoveries import calculate_top_discoveries
from mapping.mb_metadata_cache import create_mb_metadata_cache

@click.group()
def cli():
    pass


@cli.command()
def create_all():
    """
        Create all mappings in one go. First mbid mapping, then its typesense index and finally the year lookup mapping.
    """
    create_mbid_mapping()
    action_build_index()
    create_year_mapping()


@cli.command()
def mbid_mapping():
    """
        Create the MBID mapping, which also creates the prerequisit artist-credit pairs table. This can be done during
        production as new tables are moved in place atomically.
    """
    create_mbid_mapping()


@cli.command()
def test_mapping():
    """
        Test the created mbid mapping. The MBID mapping must have been created before running this.
    """
    action_test_mapping()


@cli.command()
def year_mapping():
    """
        Create the recording year lookup mapping, which also creates the prerequisit artist-credit pairs table.
        This can be done during production as new tables are moved in place atomically.
    """
    create_year_mapping()


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
def build_mb_metadata_cache():
    """
        Build the MB metadata cache that LB uses
    """
    create_mb_metadata_cache()


def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == "__main__":
    cli()
    sys.exit(0)
