#!/usr/bin/env python3

import os
import sys

import click


CRON_LOGS_DIR = "/logs"
ADMIN_CONFIG_FILE = "/code/listenbrainz/admin/config.sh"


def sanity_check():
    """ Check to make sure the logs dir exists, read the admin config file and
     check that the file contains listenbrainz-cron-prod. if not exit with success
     and not locking the cron."""
    try:
        with open(ADMIN_CONFIG_FILE, mode="r") as f:
            data = f.read()
            if "listenbrainz-cron-prod" not in data:
                print("we do not seem to be running inside the cron prod container.")
                sys.exit(0)
    except IOError:
        print("Didn't find config file, not locking cron.")
        sys.exit(-1)

    if not os.path.exists(CRON_LOGS_DIR):
        print("cron logs dir does not exist. Is this code running in the container?")
        sys.exit(-1)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('slug')
@click.argument('msg')
def lock_cron(slug, msg):
    """Lock the cron container, writing the given message into the lock file
       identified by slug."""
    sanity_check()

    cron_lock_file = os.path.join(CRON_LOGS_DIR, "cron-%s.lock" % slug)
    if os.path.exists(cron_lock_file):
        print("cron lock file exists. refusing to overwrite.")
        sys.exit(-1)

    with open(cron_lock_file, "w") as f:
        f.write(msg)
        f.write("\n")

    sys.exit(0)


@cli.command()
@click.argument('slug')
def unlock_cron(slug):
    """Unlock the cron container for the given slug"""
    sanity_check()

    cron_lock_file = os.path.join(CRON_LOGS_DIR, "cron-%s.lock" % slug)
    try:
        os.unlink(cron_lock_file)
    except FileNotFoundError:
        print("cron lock file does not exist")
        sys.exit(-1)

    sys.exit(0)


@cli.command()
def check_lock():
    """Check the state of the locks. The script exists with status 0, if no locks
       exist, 1 if one or more exists. If cron is locked, the lock message(s)
       will be printed to stdout."""
    sanity_check()

    found_locks = False
    for file_name in os.listdir(CRON_LOGS_DIR):
        if file_name.endswith(".lock"):
            with open(os.path.join(CRON_LOGS_DIR, file_name), "r") as f:
                print(f.read(), end="")
                found_locks = True

    if found_locks:
        sys.exit(1)

    sys.exit(0)


def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == "__main__":
    cli()
    sys.exit(0)
