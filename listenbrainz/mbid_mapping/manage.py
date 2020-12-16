#!/usr/bin/env python3

import sys
import os
import subprocess

import click

from mapping.mbid_mapping import create_mbid_mapping
from mapping.typesense_index import build_index as action_build_index
from mapping.year_mapping import create_year_mapping
from mapping.search import search as action_search
from mapping.mapping_test.mapping_test import test_mapping as action_test_mapping
from mapping.utils import log, CRON_LOG_FILE


@click.group()
def cli():
    pass


@cli.command()
def mbid_mapping():
    create_mbid_mapping()


@cli.command()
def test_mapping():
    action_test_mapping()


@cli.command()
def year_mapping():
    create_year_mapping()


@cli.command()
def build_index():
    action_build_index()


@cli.command()
@click.argument('query', nargs=-1)
def search(query):
    hits = action_search(" ".join(query))
    for hit in hits:
        print("%-40s %-40s %-40s" % (hit['recording_name'][:39], hit['release_name'][:39], hit['artist_credit_name'][:39]))


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
