#!/usr/bin/env python3

import sys
import os
import subprocess

import click

from mapping.msid_mapping import create_mapping as action_create_mapping
from mapping.recording_pairs import create_pairs as action_create_pairs
from mapping.test.test_mapping import test_mapping as action_test_mapping
from mapping.test.test_pairs import test_pairs as action_test_pairs
from mapping.write_mapping import write_all_mappings as action_write_all_mappings
from mapping.utils import log, CRON_LOG_FILE

@click.group()
def cli():
    pass

@cli.command()
def create_all():
    action_create_pairs()
    action_create_mapping()


@cli.command()
def create_mapping():
    action_create_mapping()


@cli.command()
def create_pairs():
    action_create_pairs()


@cli.command()
def test_mapping():
    action_test_mapping()


@cli.command()
def test_pairs():
    action_test_pairs()


@cli.command()
@click.argument("dest_dir", nargs=1)
def write(dest_dir):
    action_write_all_mappings(dest_dir)


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
