from mapping.canonical_musicbrainz_data import create_canonical_musicbrainz_data
from mapping.release_colors import incremental_update_release_color_table
from mapping.typesense_index import build_all as action_build_index
import sentry_sdk
from sentry_sdk.crons import capture_checkin
from sentry_sdk.crons.consts import MonitorStatus


def cron_wrapper_create_all():
    """ Run a monitored cron job to create the canonical data and the typesense index """

    slug='canonical-data-typesense-index'
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
