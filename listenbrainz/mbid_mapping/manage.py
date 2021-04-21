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
def cron_log():
    if os.path.exists(CRON_LOG_FILE):
        log("Current cron job log file:")
        subprocess.run(["cat", CRON_LOG_FILE])
    else:
        log("Log file is empty")


def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == "__main__":
    cli()
    sys.exit(0)
