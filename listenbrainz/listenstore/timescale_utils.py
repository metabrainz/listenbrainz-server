import logging
import subprocess
from datetime import datetime, timezone

from brainzutils import cache
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import listens as listens_db, timescale, user as db_user
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT
from listenbrainz.webserver.listens_cache import invalidate_user_listen_caches

logger = logging.getLogger(__name__)

SECONDS_IN_A_YEAR = 31536000


def delete_listens():
    """Process pending deletions in the listens database, retaining their history.

    The delete API invalidates caches when a deletion is requested, but reads can cache the
    listen again until it is actually deleted here, so invalidate the affected users again.
    """
    user_ids = listens_db.delete_pending_listens()
    for user_id in user_ids:
        cache.delete(REDIS_USER_LISTEN_COUNT + str(user_id))
        invalidate_user_listen_caches(user_id)
    logger.info("Processed pending listen deletions for %d users", len(user_ids))


def _get_user_ids():
    with db.engine.connect() as connection:
        # an aware cutoff, get_all_users' naive default would skip recent users on non-UTC hosts
        users = db_user.get_all_users(connection, created_before=datetime.now(timezone.utc), columns=["id"])
        return [user["id"] for user in users]


def add_missing_to_listen_users_metadata():
    """ Fetch users from LB and add an entry those users which are missing from listen_user_metadata """
    user_list = _get_user_ids()
    logger.info("Fetched %d users. Setting empty listen counts.", len(user_list))
    listens_db.add_missing_to_listen_user_metadata(user_list)


def recalculate_all_user_data():
    """ Recalculate the listen counts of all users from scratch """
    user_list = _get_user_ids()
    logger.info("Fetched %d users. Recalculating listen counts.", len(user_list))
    listens_db.recalculate_listen_counts(user_list)
    logger.info("Recalculated listen counts for all users")


def unlock_cron():
    """ Unlock the cron container """

    # Unlock the cron container
    try:
        subprocess.run(["/usr/local/bin/python", "admin/cron_lock.py", "unlock-cron", "cont-agg"])
    except subprocess.CalledProcessError as err:
        logger.error("Cannot unlock cron after updating continuous aggregates: %s" % str(err))


def refresh_top_manual_mappings():
    """ Refresh top manual msid-mbid mappings view """
    with timescale.engine.begin() as ts_conn:
        ts_conn.execute(text("REFRESH MATERIALIZED VIEW mbid_manual_mapping_top"))


class TimescaleListenStoreException(Exception):
    pass
