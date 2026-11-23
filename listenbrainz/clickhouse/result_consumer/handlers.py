import re
from functools import wraps

import requests
from flask import current_app
from requests import HTTPError

from listenbrainz.db import couchdb, stats


def handle_dump_imported(message):
    """Handle the success or failure of a dump import."""
    dump_type = message.get("dump_type", "unknown")
    dump_id = message.get("dump_id")
    status = message.get("status", "unknown")
    total_inserted = message.get("total_inserted", 0)
    added = message.get("added", 0)
    pending = message.get("pending")
    error = message.get("error")

    remaining = f", {pending} dump(s) still pending" if pending else ""

    if status == "success":
        current_app.logger.info(
            f"ClickHouse dump import complete: type={dump_type}, id={dump_id}, "
            f"listens in dump={total_inserted}, new listens={added}{remaining}"
        )
    else:
        current_app.logger.error(
            f"ClickHouse dump import failed: type={dump_type}, id={dump_id}, error={error}{remaining}"
        )


def handle_schema_initialized(message):
    """Handle the success or failure of ClickHouse schema initialization."""
    status = message.get("status", "unknown")
    if status == "success":
        current_app.logger.info("ClickHouse schema initialized")
    else:
        current_app.logger.error("ClickHouse schema initialization failed: %s", message.get("error"))


class RetryClickHouseResult(RuntimeError):
    """Ask the consumer to requeue this delivery."""


def _handle_couchdb_errors(handler):
    @wraps(handler)
    def wrapped(message):
        try:
            return handler(message)
        except (couchdb.RetryableDocumentError, requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError) as exc:
            raise RetryClickHouseResult(f"Retrying {message['type']} after a CouchDB failure") from exc
        except requests.RequestException as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in (408, 429) or (status is not None and status >= 500):
                raise RetryClickHouseResult(f"Retrying {message['type']} after CouchDB returned {status}") from exc
            current_app.logger.exception("Permanent HTTP failure in ClickHouse handler for '%s'", message["type"])

    return wrapped


@_handle_couchdb_errors
def handle_daily_activity_start(message):
    try:
        couchdb.create_database(message["database"])
    except HTTPError as exc:
        if exc.response.status_code != 412:  # Replay of a start message.
            raise


@_handle_couchdb_errors
def handle_daily_activity(message):
    stats.insert(message["database"], message["from_ts"], message["to_ts"], message["data"])


@_handle_couchdb_errors
def handle_daily_activity_end(message):
    database = message["database"]
    if not re.fullmatch(r"clickhouse_daily_activity_[a-z_]+_[0-9]{20}", database):
        raise ValueError(f"Invalid daily activity database {database}")
    # Keep the previous generation if a batch failed to reach CouchDB.
    if couchdb.get_document_count(database) != message["user_count"]:
        raise ValueError(f"Incomplete daily activity database {database}")
    prefix = database.rsplit("_", 1)[0] + "_"
    couchdb.delete_database(prefix, older_than=database)


RESPONSE_HANDLERS = {
    "clk_daily_activity_start": handle_daily_activity_start,
    "clk_daily_activity": handle_daily_activity,
    "clk_daily_activity_end": handle_daily_activity_end,
    "clk_dump_import": handle_dump_imported,
    "clk_schema_initialization": handle_schema_initialized,
}


def get_handler(message_type: str):
    """Get the handler function for a message type."""
    return RESPONSE_HANDLERS.get(message_type)
