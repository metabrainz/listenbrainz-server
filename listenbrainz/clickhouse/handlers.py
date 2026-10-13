import logging
from datetime import datetime, timezone

from flask import current_app
from requests import HTTPError
from sentry_sdk import start_transaction

import listenbrainz.db.couchdb as couchdb
import listenbrainz.db.stats as db_stats
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_listening_activity import ListeningActivityRecord


logger = logging.getLogger(__name__)

# The user stats computed by the ClickHouse pipeline and the models their entries are
# validated with.
ENTITY_MODELS = {
    "daily_activity": DailyActivityRecord,
    "listening_activity": ListeningActivityRecord,
}


# CouchDB errors are not caught by the handlers below: the ClickHouse side has already
# marked these stats as computed, so the reader requeues a message whose write failed
# with a transient error instead of dropping it.


def handle_stats_database_start(message):
    """
    Handle start of a stats database refresh.
    Creates the database for the incoming data.
    """
    database = message.get("database")
    if not database:
        current_app.logger.error("No database specified in clk_stats_database_start message")
        return

    match = couchdb.DATABASE_NAME_PATTERN.match(database)
    if not match:
        current_app.logger.error(f"Invalid database name format: {database}")
        return

    try:
        couchdb.create_database(database)
        current_app.logger.info(f"Created CouchDB database: {database}")
    except HTTPError as e:
        # 412: the database already exists
        if e.response.status_code != 412:
            raise


def handle_stats_database_end(message):
    """
    Handle end of a stats database refresh.
    Cleans up old databases of the same type.
    """
    database = message.get("database")
    if not database:
        current_app.logger.error("No database specified in clk_stats_database_end message")
        return

    match = couchdb.DATABASE_NAME_PATTERN.match(database)
    if not match:
        current_app.logger.error(f"Invalid database name format: {database}")
        return

    # Delete old databases, keeping the latest
    prefix = f"{match[1]}_{match[2]}"
    _, retained = couchdb.delete_database(prefix)
    if retained:
        current_app.logger.info(f"Databases retained (locked): {retained}")


def handle_user_entity_stats(message):
    """
    Handle batched user stats (daily_activity, listening_activity) from ClickHouse.
    Inserts the stats data into CouchDB using bulk insert.

    Message format:
        {
            'type': 'clk_user_entity',
            'entity': 'daily_activity',
            'stats_range': 'all_time',
            'from_ts': 0,
            'to_ts': 1234567890,
            'database': 'clk_daily_activity_all_time_20240115',
            'data': [
                {'user_id': 123, 'count': 100, 'data': [...]},
                {'user_id': 456, 'count': 50, 'data': [...]},
                ...
            ]
        }
    """
    entity = message.get("entity")
    stats_range = message.get("stats_range")
    from_ts = message.get("from_ts")
    to_ts = message.get("to_ts")
    database = message.get("database")
    database_prefix = message.get("database_prefix")
    batch_data = message.get("data", [])

    if not all([entity, stats_range]) or from_ts is None or to_ts is None or not (database or database_prefix):
        current_app.logger.error(f"Missing required fields in clk_user_entity message: {message}")
        return

    if not batch_data:
        current_app.logger.warning(f"Empty data in clk_user_entity message for {entity}/{stats_range}")
        return

    model = ENTITY_MODELS.get(entity)
    if model is None:
        current_app.logger.error(f"Unknown ClickHouse entity stats type: {entity}")
        return

    if database_prefix:
        databases = couchdb.list_databases(database_prefix)
        if databases:
            database = databases[0]
        else:
            database = f"{database_prefix}_{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}"
            try:
                couchdb.create_database(database)
            except HTTPError as e:
                if e.response.status_code != 412:
                    raise

    docs = []
    for user_stats in batch_data:
        if "user_id" not in user_stats:
            current_app.logger.warning(f"Missing user_id in batch item: {user_stats}")
            continue

        stats_data = []
        invalid_count = 0
        for item in user_stats.get("data", []):
            try:
                model(**item)
            except Exception:
                invalid_count += 1
                current_app.logger.warning("Invalid ClickHouse %s stats entry skipped: %s", entity, item)
            else:
                stats_data.append(item)

        raw_count = user_stats.get("count")
        count = len(stats_data) if raw_count is None else max(0, raw_count - invalid_count)

        docs.append({
            "user_id": user_stats["user_id"],
            "count": count,
            "data": stats_data,
        })

    if not docs:
        return

    with start_transaction(op="insert", name=f"insert clk user {entity} - {stats_range} stats batch"):
        db_stats.insert(database, from_ts, to_ts, docs)
        current_app.logger.debug(f"Inserted {len(docs)} {entity} stats docs into {database}")


def handle_dump_imported(message):
    """Handle notification that a dump was successfully imported."""
    dump_type = message.get("dump_type", "unknown")
    dump_id = message.get("dump_id")
    status = message.get("status", "unknown")
    total_inserted = message.get("total_inserted", 0)
    pending = message.get("pending")
    error = message.get("error")
    # an incremental import loads the whole backlog, so say how much of it is left
    remaining = f", {pending} dump(s) still pending" if pending else ""

    if status == "success":
        current_app.logger.info(
            f"ClickHouse dump import complete: type={dump_type}, id={dump_id}, "
            f"inserted={total_inserted}{remaining}"
        )
    else:
        current_app.logger.error(
            f"ClickHouse dump import failed: type={dump_type}, id={dump_id}, error={error}{remaining}"
        )


def handle_dump_import_recorded(message):
    """Handle notification that a dump was recorded as already loaded."""
    dump_type = message.get("dump_type", "unknown")
    dump_id = message.get("dump_id")
    status = message.get("status", "unknown")
    error = message.get("error")

    if status == "success":
        current_app.logger.info(
            f"ClickHouse dump recorded as imported: type={dump_type}, id={dump_id}, "
            f"imported_at={message.get('imported_at') or 'now'}"
        )
    else:
        current_app.logger.error(
            f"ClickHouse dump could not be recorded as imported: id={dump_id}, error={error}"
        )


def handle_stats_complete(message):
    """Handle notification that stats processing is complete."""
    job = message.get("job", "unknown")
    entities = message.get("entities", [])
    current_app.logger.info(
        f"ClickHouse stats job complete: job={job}, entities={entities}"
    )


def handle_stats_error(message):
    """Handle notification of stats processing error."""
    entity = message.get("entity", "unknown")
    job = message.get("job", "unknown")
    error = message.get("error", "unknown error")
    current_app.logger.error(
        f"ClickHouse stats error: job={job}, entity={entity}, error={error}"
    )


def handle_deleted_listens_imported(message):
    """Handle notification that listen deletions were applied to ClickHouse."""
    status = message.get("status", "unknown")
    if status == "success":
        current_app.logger.info(
            "ClickHouse deleted listens import complete: %d deleted listens (%d removed), "
            "%d deleted user histories (%d listens removed)",
            message.get("deleted_listens_imported", 0), message.get("deleted_listens_removed", 0),
            message.get("deleted_user_histories_imported", 0), message.get("deleted_user_listens_removed", 0),
        )
    else:
        current_app.logger.error("ClickHouse deleted listens import failed: %s", message.get("error"))


def handle_schema_initialized(message):
    """Handle notification that the ClickHouse schema was initialized."""
    status = message.get("status", "unknown")
    if status == "success":
        current_app.logger.info("ClickHouse schema initialized")
    else:
        current_app.logger.error("ClickHouse schema initialization failed: %s", message.get("error"))


RESPONSE_HANDLERS = {
    "clk_stats_database_start": handle_stats_database_start,
    "clk_stats_database_end": handle_stats_database_end,
    "clk_user_entity": handle_user_entity_stats,
    "clk_dump_imported": handle_dump_imported,
    "clk_dump_import_recorded": handle_dump_import_recorded,
    "clk_stats_complete": handle_stats_complete,
    "clk_stats_error": handle_stats_error,
    "clk_schema_initialized": handle_schema_initialized,
    "clk_deleted_listens_imported": handle_deleted_listens_imported,
}


def get_handler(message_type: str):
    """Get the handler function for a message type."""
    return RESPONSE_HANDLERS.get(message_type)
