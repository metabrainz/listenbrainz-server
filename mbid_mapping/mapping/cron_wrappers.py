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
import config

import sentry_sdk
from sentry_sdk.crons import capture_checkin
from sentry_sdk.crons.consts import MonitorStatus


def cron_wrapper_create_all():
    """ Run a monitored cron job to create the canonical data and the typesense index """

    slug = 'canonical-data-typesense-index'
    sentry_sdk.init(config.LOG_SENTRY["dsn"])
    check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)

    try:
        create_canonical_musicbrainz_data(True)
        action_build_index()
    except Exception as err:
        print("Exception: %s" % err)
        capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
        return

    capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)


def cron_incremental_update_release_color_table():
    """ Update the release_colors table. """

    slug = 'caa-color-sync'
    sentry_sdk.init(config.LOG_SENTRY["dsn"])
    check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)

    try:
        incremental_update_release_color_table()
    except Exception as err:
        print("Exception: %s" % err)
        capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
        return

    capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)


def cron_create_spotify_metadata_index(use_lb_conn):
    """ Update the spotify metadata index via cron """

    slug = 'create-spotify-metadata-index'
    sentry_sdk.init(config.LOG_SENTRY["dsn"])
    check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)

    try:
        create_spotify_metadata_index(use_lb_conn)
    except Exception as err:
        print("Exception: %s" % err)
        capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
        return

    capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)


def cron_create_apple_metadata_index(use_lb_conn):
    """ Update the apple metadata index via cron """

    slug = 'create-apple-metadata-index'
    sentry_sdk.init(config.LOG_SENTRY["dsn"])
    check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)

    try:
        create_apple_metadata_index(use_lb_conn)
    except Exception as err:
        print("Exception: %s" % err)
        capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
        return

    capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)


def cron_create_soundcloud_metadata_index(use_lb_conn):
    """ Update the soundcloud metadata index via cron """

    slug = 'create-soundcloud-metadata-index'
    sentry_sdk.init(config.LOG_SENTRY["dsn"])
    check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)

    try:
        create_soundcloud_metadata_index(use_lb_conn)
    except Exception as err:
        print("Exception: %s" % err)
        capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
        return

    capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)


def cron_create_tag_similarity():
    """ Update the tag similarity data via cron """

    slug = 'create-tag-similarity'
    sentry_sdk.init(config.LOG_SENTRY["dsn"])
    check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)

    try:
        create_tag_similarity()
    except Exception as err:
        print("Exception: %s" % err)
        capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
        return

    capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)


def cron_build_all_mb_caches():
    """ build all mb caches via cron """

    slug = 'build-all-mb-caches'
    sentry_sdk.init(config.LOG_SENTRY["dsn"])
    check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)

    try:
        create_mb_metadata_cache(True)
        cleanup_mbid_mapping_table()
        create_mb_artist_metadata_cache(True)
        create_mb_release_group_cache(True)
    except Exception as err:
        print("Exception: %s" % err)
        capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
        return

    capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)


def cron_update_all_mb_caches():
    """ Update all mb caches via cron """

    slug = 'update-all-mb-caches'
    sentry_sdk.init(config.LOG_SENTRY["dsn"])
    check_in_id = capture_checkin(monitor_slug=slug, status=MonitorStatus.IN_PROGRESS)

    try:
        update_canonical_release_data(False)
        incremental_update_mb_metadata_cache(True)
        incremental_update_mb_artist_metadata_cache(True)
        incremental_update_mb_release_group_cache(True)

    except Exception as err:
        print("Exception: %s" % err)
        capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.ERROR)
        return

    capture_checkin(monitor_slug=slug, check_in_id=check_in_id, status=MonitorStatus.OK)
