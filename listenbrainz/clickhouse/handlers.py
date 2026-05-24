import logging
from datetime import datetime, timezone

from flask import current_app
from requests import HTTPError
from sentry_sdk import start_transaction

import listenbrainz.db.couchdb as couchdb
import listenbrainz.db.stats as db_stats
from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_group_stat import ReleaseGroupRecord


logger = logging.getLogger(__name__)

ENTITY_MODELS = {
    "artists": ArtistRecord,
    "recordings": RecordingRecord,
    "release_groups": ReleaseGroupRecord,
}


def handle_echo(message):
    """Echo handler for testing connectivity."""
    current_app.logger.info(f"ClickHouse echo: {message.get('message', 'no message')}")


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
        # Create database with format: prefix_range_YYYYMMDD
        db_name = f"{match[1]}_{match[2]}_{match[3]}"
        couchdb.create_database(db_name)
        current_app.logger.info(f"Created CouchDB database: {db_name}")
    except HTTPError as e:
        if e.response.status_code != 412:
            current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


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

    try:
        # Delete old databases, keeping the latest
        prefix = f"{match[1]}_{match[2]}"
        _, retained = couchdb.delete_database(prefix)
        if retained:
            current_app.logger.info(f"Databases retained (locked): {retained}")
    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


def handle_user_entity_stats(message):
    """
    Handle batched user entity stats (artists, recordings, release_groups) from ClickHouse.
    Inserts the stats data into CouchDB using bulk insert.

    Message format:
        {
            'type': 'clk_user_entity',
            'entity': 'artists',
            'stats_range': 'all_time',
            'from_ts': 0,
            'to_ts': 1234567890,
            'database': 'clk_artists_all_time_20240115',
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
                    current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)
                    return

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

    try:
        with start_transaction(op="insert", name=f"insert clk user {entity} - {stats_range} stats batch"):
            db_stats.insert(database, from_ts, to_ts, docs)
            current_app.logger.debug(f"Inserted {len(docs)} {entity} stats docs into {database}")
    except HTTPError as e:
        current_app.logger.error(f"Error inserting stats batch: {e}. Response: %s", e.response.json(), exc_info=True)
    except Exception as e:
        current_app.logger.error(f"Error inserting stats batch: {e}", exc_info=True)


def handle_dump_imported(message):
    """Handle notification that a dump was successfully imported."""
    dump_type = message.get("dump_type", "unknown")
    dump_id = message.get("dump_id")
    status = message.get("status", "unknown")
    total_inserted = message.get("total_inserted", 0)
    error = message.get("error")

    if status == "success":
        current_app.logger.info(
            f"ClickHouse dump import complete: type={dump_type}, id={dump_id}, inserted={total_inserted}"
        )
    else:
        current_app.logger.error(
            f"ClickHouse dump import failed: type={dump_type}, error={error}"
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


def handle_metadata_cache_refresh(message):
    """Handle notification that a metadata cache refresh completed."""
    status = message.get("status", "unknown")
    results = message.get("results", {})
    error = message.get("error")
    if status == "success":
        current_app.logger.info("ClickHouse metadata cache refresh complete: %s", results)
    else:
        current_app.logger.error("ClickHouse metadata cache refresh failed: results=%s error=%s", results, error)


RESPONSE_HANDLERS = {
    "echo": handle_echo,
    "clk_stats_database_start": handle_stats_database_start,
    "clk_stats_database_end": handle_stats_database_end,
    "clk_user_entity": handle_user_entity_stats,
    "clk_dump_imported": handle_dump_imported,
    "clk_stats_complete": handle_stats_complete,
    "clk_stats_error": handle_stats_error,
    "clk_metadata_cache_refresh": handle_metadata_cache_refresh,
}


def get_handler(message_type: str):
    """Get the handler function for a message type."""
    return RESPONSE_HANDLERS.get(message_type)
