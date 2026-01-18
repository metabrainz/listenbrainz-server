import logging
from datetime import datetime, timezone

from flask import current_app
from requests import HTTPError
from sentry_sdk import start_transaction

import listenbrainz.db.couchdb as couchdb


logger = logging.getLogger(__name__)


def handle_echo(message):
    """Echo handler for testing connectivity."""
    current_app.logger.info(f"ClickHouse echo: {message.get('message', 'no message')}")


def handle_couchdb_data_start(message):
    """
    Handle start of a CouchDB bulk data operation.
    Creates the database for the incoming data.
    """
    database = message.get("database")
    if not database:
        current_app.logger.error("No database specified in couchdb_data_start message")
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
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


def handle_couchdb_data_end(message):
    """
    Handle end of a CouchDB bulk data operation.
    Cleans up old databases of the same type.
    """
    database = message.get("database")
    if not database:
        current_app.logger.error("No database specified in couchdb_data_end message")
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
            'entity_type': 'artist',
            'time_range': 'all_time',
            'database': 'clk_artist_all_time',
            'data': [
                {'user_id': 123, 'count': 100, 'artist': [...]},
                {'user_id': 456, 'count': 50, 'artist': [...]},
                ...
            ]
        }
    """
    entity_type = message.get("entity_type")
    time_range = message.get("time_range")
    database = message.get("database")
    batch_data = message.get("data", [])

    if not all([entity_type, time_range, database]):
        current_app.logger.error(f"Missing required fields in clk_user_entity message: {message}")
        return

    if not batch_data:
        current_app.logger.warning(f"Empty data in clk_user_entity message for {entity_type}/{time_range}")
        return

    # Build docs from batched data
    docs = []
    last_updated = int(datetime.now(tz=timezone.utc).timestamp())

    for user_stats in batch_data:
        user_id = user_stats.get("user_id")
        count = user_stats.get("count", 0)
        stats_data = user_stats.get(entity_type, [])

        if user_id is None:
            current_app.logger.warning(f"Missing user_id in batch item: {user_stats}")
            continue

        doc = {
            "_id": str(user_id),
            "user_id": user_id,
            "count": count,
            "last_updated": last_updated,
            entity_type: stats_data,
        }
        docs.append(doc)

    if not docs:
        return

    try:
        with start_transaction(op="insert", name=f"insert clk user {entity_type} - {time_range} stats batch"):
            # Ensure database exists
            couchdb.create_database(database)
            # Insert all documents in batch
            couchdb.insert_data(database, docs)
            current_app.logger.debug(f"Inserted {len(docs)} {entity_type} stats docs into {database}")
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


RESPONSE_HANDLERS = {
    "echo": handle_echo,
    "couchdb_data_start": handle_couchdb_data_start,
    "couchdb_data_end": handle_couchdb_data_end,
    "clk_user_entity": handle_user_entity_stats,
    "clk_dump_imported": handle_dump_imported,
    "clk_stats_complete": handle_stats_complete,
    "clk_stats_error": handle_stats_error,
}


def get_handler(message_type: str):
    """Get the handler function for a message type."""
    return RESPONSE_HANDLERS.get(message_type)
