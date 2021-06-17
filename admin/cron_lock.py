#!/usr/bin/env python3

import os
import sys

import click


CRON_LOGS_DIR = "/logs"
CRON_LOCK_FILE = os.path.join(CRON_LOGS_DIR, "cron.lock")


def sanity_check():
    """ Check to make sure the logs dir exists and that the CONTAINER_NAME env
        var is set correctly for the cron container. If the PROD_ENV var is not
        set, assume that we are not running in production and exist with success. """

    if "PROD_ENV" not in os.environ:
        print("Not running in a production env, not locking cron.")
        sys.exit(0)

    if not os.path.exists(CRON_LOGS_DIR):
        print("cron logs dir does not exist. Is this code running in the container?")
        sys.exit(-1)

    if "CONTAINER_NAME" not in os.environ or os.environ["CONTAINER_NAME"] != "listenbrainz-cron-prod":
        print("we do not seem to be running inside the cron prod container.")
        sys.exit(-1)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('msg')
def lock_cron(msg):
    """Lock the cron container, writing the given message into the lock file."""
    sanity_check()

    if os.path.exists(CRON_LOCK_FILE):
        print("cron lock file exists. refusing to overwrite.")
        sys.exit(-1)

    with open(CRON_LOCK_FILE, "w") as f:
        f.write(msg)
        f.write("\n")

    sys.exit(0)


@cli.command()
def unlock_cron():
    """Unlock the cron container"""
    sanity_check()

    try:
        os.unlink(CRON_LOCK_FILE)
    except FileNotFoundError:
        print("cron lock file does not exist")
        sys.exit(-1)

    sys.exit(0)


@cli.command()
def check_lock():
    """Check the state of the lock. The script exists with status 0, if the lock
       does not exist, 1 if it exists. If cron is locked, the lock message
       will be printed to stdout."""
    sanity_check()

    if os.path.exists(CRON_LOCK_FILE):
        with open(CRON_LOCK_FILE, "r") as f:
            print(f.read(), end="")
        sys.exit(1)

    sys.exit(0)


def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == "__main__":
    cli()
    sys.exit(0)
