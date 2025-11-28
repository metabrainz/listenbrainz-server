#!/usr/bin/env python3

import datetime
from functools import wraps
import os
import sys
from time import time
import traceback

import click
import requests
import psutil


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
from mapping.utils import log
from brainzutils import cache


def check_in(slug):
    """ Call heathchecks.io cron check-in with the given slug """

    url = f"https://hc-ping.com/{config.PING_KEY}/{slug}"
    r = requests.get(url)
    r.raise_for_status()
    
"""
Rebuild:

1. Check for lock (timestamp, pid, epoch time)
2. If present and pid still exists, sleep for 60 seconds.
3. Otherwise set lock and proceed

Incremental:

1. Check for lock
2. If present and pid still exists, exit.
3. If lock not present or pid no longer exists, set lock, proceed.
"""

CACHE_LOCK_KEY = "cache-rebuild-lock"
CACHE_REBUILD_SLEEP_TIME = 60

def cache_lock_rebuild():
    """ Set the cache lock in redis for the rebuild process"""
    cache.init(host=config.REDIS_HOST, port=int(config.REDIS_PORT), namespace=config.REDIS_NAMESPACE)

    while True: 
        value = "%d-%d" % (os.getpid(), int(time()))
        lock_value = cache._r.setnx(CACHE_LOCK_KEY, value)
        
        # Did we succeed in setting the lock?
        if lock_value == value:
            log("Cache lock set for rebuild")
            # Yep, we're good to go.
            return
        else:
            # Nope, check to see if proc still exists
            pid, _ = value.split("-")
            if psutil.pid_exists(int(pid)):
                log("Cache lock pid exists")
                sleep(CACHE_REBUILD_SLEEP_TIME)
                continue
            else:
                log("Cache lock pid no longer exists")

        log("Set cache lock for rebuild")
        # That proc no longer exists, set key and proceed
        cache._r.set(CACHE_LOCK_KEY, value)
        break

def cache_lock_incremental():
    """ Set the cache lock in redis for the incremental process"""
    cache.init(host=config.REDIS_HOST, port=int(config.REDIS_PORT), namespace=config.REDIS_NAMESPACE)

    value = "%d-%d" % (os.getpid(), int(time()))
    lock_value = cache._r.setnx(CACHE_LOCK_KEY, value)
    
    # Did we succeed in setting the lock?
    if lock_value == value:
        log("Cache lock set for incremental")
        # Yep, we're good to go.
        return
    else:
        # Nope, check to see if proc still exists
        pid, _ = value.split("-")
        if psutil.pid_exists(int(pid)):
            log("Cache lock pid exists")
            return

    log("Set cache lock for incremental")
    # That proc no longer exists, set key and proceed
    cache._r.set(CACHE_LOCK_KEY, value)
    
def cache_lock_cleanup():
    """Release the cache lock"""
    cache._r.delete(CACHE_LOCK_KEY)

def cron(slug):
    """ Cron decorator making it easy to monitor a cron job. The slug argument defines the sentry cron job identifier. """
    def wrapper(func):
        log("process %d starting" % os.getpid())
        @wraps(func)
        def wrapped_f(*args, **kwargs):
            try:
                func(*args, **kwargs)
                check_in(slug)
            except Exception:
                traceback.print_exc()
                sys.exit(-1)

        return wrapped_f

    return wrapper


@click.group()
def cli():
    pass

@cli.command()
@cron("canonical-data-typesense-index")
def cron_create_all():
    """
        Create all canonical data in one go as a monitored cron job. First mb canonical data, then its typesense index.
    """
    create_canonical_musicbrainz_data(True)
    action_build_index()


@cli.command()
@cron("caa-color-sync")
def cron_update_coverart():
    """
        Update the release_color table incrementally. Designed to be called hourly by cron.
    """
    incremental_update_release_color_table()


@cli.command()
@cron("build-mb-metadata-cache")
def cron_build_mb_metadata_cache():
    """ Build the mb metadata cache and tables it depends on in production in appropriate databases.
     After building the cache, cleanup mbid_mapping table.
    """
    create_mb_metadata_cache(True)
    cleanup_mbid_mapping_table()


@cli.command()
@cron("cron-build-all-mb-caches")
def cron_build_all_mb_caches():
    """Full rebuild all mb entity metadata cache and tables it depends on in production in appropriate
     databases. After building the cache, cleanup mbid_mapping table.
    """

    log("start full")
    cache_lock_rebuild()
    log("got full lock")
    
    log("create mb metadata cache")
    create_mb_metadata_cache(True)
    log("cleanup mbid mapping table")
    cleanup_mbid_mapping_table()
    log("create artist metadata cache")
    create_mb_artist_metadata_cache(True)
    log("create release group metadata cache")
    create_mb_release_group_cache(True)

    cache_lock_cleanup()
    log("full complete")

@cli.command()
@cron("update-all-mb-caches")
def cron_update_all_mb_caches():
    """ Update all mb entity metadata cache in ListenBrainz incrementally. """

    log("start incremental")
    try:
        cache_lock_incremental()
    except Exception as err:
        traceback.print_exc()
        print(err)
        raise

    log("got incremental lock")

    update_canonical_release_data(False)
    incremental_update_mb_metadata_cache(True)
    incremental_update_mb_artist_metadata_cache(True)
    incremental_update_mb_release_group_cache(True)

    cache_lock_cleanup()
    log("incremental complete")

@cli.command()
@cron("create-spotify-metadata-index")
def cron_build_spotify_metadata_index():
    """
        Build the spotify metadata index that LB uses invoked via cron
    """
    create_spotify_metadata_index(True)


@cli.command()
@cron("create-apple-metadata-index")
def cron_build_apple_metadata_index():
    """
        Build the Apple Music metadata index that LB uses invoked from cron
    """
    create_apple_metadata_index(True)


@cli.command()
@cron("create-soundcloud-metadata-index")
def cron_build_soundcloud_metadata_index():
    """
        Build the Soundcloud Music metadata index that LB usesa invoked from cron
    """
    create_soundcloud_metadata_index(True)


@cli.command()
@cron("create-tag-similarity")
def cron_build_tag_similarity():
    """
        Build the tag similarity data invoked via cron
    """
    create_tag_similarity()
