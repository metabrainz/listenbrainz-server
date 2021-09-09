#!/usr/bin/env python3

import os
import time
import sys

import click

import mapping.release_lookup as ri


@click.group()
def cli():
    pass

@cli.command()
@click.argument('release_mbid', nargs=1)
def fetch(release_mbid):
    rel = ri.musicbrainz_lookup(release_mbid)
    print(json.dumps(rel, indent=4, sort_keys=True))

@cli.command()
@click.argument('release_mbid', nargs=1)
def check(release_mbid):
    ri.musicbrainz_sanity_check(release_mbid)

@cli.command()
@click.argument('user_name', nargs=1)
@click.argument('count', nargs=1, required=False, default=1000)
@click.argument('ts', nargs=1, required=False, default=None)
def filter(user_name, count, ts):
    ri.listenbrainz_release_filter(user_name, count, ts, True)

@cli.command()
def test():
    ri.test_compare_releases()

def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == "__main__":
    cli()
    sys.exit(0)
