#!/usr/bin/env python3

import sys
import os
import subprocess

import click

from mapping.cron_wrappers import cron_wrapper_create_all, \
                                  cron_incremental_update_release_color_table, \
                                  cron_create_spotify_metadata_index, \
                                  cron_create_apple_metadata_index, \
                                  cron_create_soundcloud_metadata_index, \
                                  cron_build_all_mb_caches as cron_wrapper_cron_build_all_mb_caches, \
                                  cron_update_all_mb_caches as cron_wrapper_cron_update_all_mb_caches, \
                                  cron_wrapper_create_all, \
                                  cron_create_tag_similarity


@click.group()
def cli():
    pass


@cli.command()
def cron_create_all():
    """
        Create all canonical data in one go as a monitored cron job. First mb canonical data, then its typesense index.
    """
    cron_wrapper_create_all()


@cli.command()
def cron_update_coverart():
    """
        Update the release_color table incrementally. Designed to be called hourly by cron.
    """
    cron_incremental_update_release_color_table()


@cli.command()
def log():
    """
        Print the internal cron log file for debugging purposes.
    """
    if os.path.exists(CRON_LOG_FILE):
        log("Current cron job log file:")
        subprocess.run(["cat", CRON_LOG_FILE])
    else:
        log("Log file is empty")


@cli.command()
def cron_build_mb_metadata_cache():
    """ Build the mb metadata cache and tables it depends on in production in appropriate databases.
     After building the cache, cleanup mbid_mapping table.
    """
    create_mb_metadata_cache(True)
    cleanup_mbid_mapping_table()


@cli.command()
@click.pass_context
def cron_build_all_mb_caches(ctx):
    """ Build all mb entity metadata cache and tables it depends on in production in appropriate
     databases. After building the cache, cleanup mbid_mapping table.
    """
    cron_wrapper_cron_build_all_mb_caches()


@cli.command()
@click.pass_context
def cron_update_all_mb_caches(ctx):
    """ Update all mb entity metadata cache in ListenBrainz. """
    cron_wrapper_cron_update_all_mb_caches()


@cli.command()
@click.option("--use-lb-conn/--use-mb-conn", default=True, help="whether to create the tables in LB or MB")
def build_cron_spotify_metadata_index(use_lb_conn):
    """
        Build the spotify metadata index that LB uses invoked via cron
    """
    cron_create_spotify_metadata_index(use_lb_conn)


@cli.command()
@click.option("--use-lb-conn/--use-mb-conn", default=True, help="whether to create the tables in LB or MB")
def cron_build_apple_metadata_index(use_lb_conn):
    """
        Build the Apple Music metadata index that LB uses invoked from cron
    """
    cron_create_apple_metadata_index(use_lb_conn)


@cli.command()
@click.option("--use-lb-conn/--use-mb-conn", default=True, help="whether to create the tables in LB or MB")
def cron_build_soundcloud_metadata_index(use_lb_conn):
    """
        Build the Soundcloud Music metadata index that LB usesa invoked from cron
    """
    cron_create_soundcloud_metadata_index(use_lb_conn)


@cli.command()
def cron_build_tag_similarity():
    """
        Build the tag similarity data invoked via cron
    """
    cron_create_tag_similarity()
