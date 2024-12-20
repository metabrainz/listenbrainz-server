#!/usr/bin/env python3
import sys
import os
import subprocess

import click
import sentry_sdk
from sentry_sdk.crons import capture_checkin
from sentry_sdk.crons.consts import MonitorStatus

import config
from mapping.canonical_musicbrainz_data import create_canonical_musicbrainz_data, update_canonical_release_data
from mapping.release_colors import incremental_update_release_color_table
from mapping.typesense_index import build_all as action_build_index
from mapping.spotify_metadata_index import create_spotify_metadata_index
from mapping.apple_metadata_index import create_apple_metadata_index
from mapping.soundcloud_metadata_index import create_soundcloud_metadata_index
from mapping.mb_metadata_cache import cleanup_mbid_mapping_table, create_mb_metadata_cache, incremental_update_mb_metadata_cache
from mapping.mb_artist_metadata_cache import create_mb_artist_metadata_cache, \
    incremental_update_mb_artist_metadata_cache
from mapping.mb_release_group_cache import create_mb_release_group_cache, incremental_update_mb_release_group_cache
from similar.tag_similarity import create_tag_similarity


def cron(slug):

    def wrapper(func):

        def wrapped_f(*args):
            sentry_sdk.init(config.LOG_SENTRY["dsn"])
            check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)
            try:
                func(*args)
            except Exception as err:
                print("Exception: %s" % err)
                capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
                return

            capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)

        return wrapped_f

    return wrapper


@click.group()
def cli():
    pass


@cron("canonical-data-typesense-index")
@cli.command()
def cron_create_all():
    """
        Create all canonical data in one go as a monitored cron job. First mb canonical data, then its typesense index.
    """
    create_canonical_musicbrainz_data(True)
    action_build_index()


@cron("caa-color-sync")
@cli.command()
def cron_update_coverart():
    """
        Update the release_color table incrementally. Designed to be called hourly by cron.
    """
    incremental_update_release_color_table()


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


@cron("build-mb-metadata-cache")
@cli.command()
def cron_build_mb_metadata_cache():
    """ Build the mb metadata cache and tables it depends on in production in appropriate databases.
     After building the cache, cleanup mbid_mapping table.
    """
    create_mb_metadata_cache(True)
    cleanup_mbid_mapping_table()


@cron("build-all-mb-caches")
@cli.command()
def cron_build_all_mb_caches():
    """ Build all mb entity metadata cache and tables it depends on in production in appropriate
     databases. After building the cache, cleanup mbid_mapping table.
    """
    create_mb_metadata_cache(True)
    cleanup_mbid_mapping_table()
    create_mb_artist_metadata_cache(True)
    create_mb_release_group_cache(True)



@cron("update-all-mb-caches")
@cli.command()
def cron_update_all_mb_caches():
    """ Update all mb entity metadata cache in ListenBrainz. """
    update_canonical_release_data(False)
    incremental_update_mb_metadata_cache(True)
    incremental_update_mb_artist_metadata_cache(True)
    incremental_update_mb_release_group_cache(True)


@cron("create-spotify-metadata-index")
@cli.command()
def build_cron_spotify_metadata_index(use_lb_conn):
    """
        Build the spotify metadata index that LB uses invoked via cron
    """
    create_spotify_metadata_index(True)


@cron("create-apple-metadata-index")
@cli.command()
def cron_build_apple_metadata_index():
    """
        Build the Apple Music metadata index that LB uses invoked from cron
    """
    create_apple_metadata_index(True)


@cron("create-soundcloud-metadata-index")
@cli.command()
def cron_build_soundcloud_metadata_index():
    """
        Build the Soundcloud Music metadata index that LB usesa invoked from cron
    """
    create_soundcloud_metadata_index(True)


@cron("create-tag-similarity")
@cli.command()
def cron_build_tag_similarity():
    """
        Build the tag similarity data invoked via cron
    """
    create_tag_similarity()
