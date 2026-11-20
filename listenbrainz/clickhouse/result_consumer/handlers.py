from flask import current_app


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


RESPONSE_HANDLERS = {
    "clk_dump_import": handle_dump_imported,
    "clk_schema_initialization": handle_schema_initialized,
}


def get_handler(message_type: str):
    """Get the handler function for a message type."""
    return RESPONSE_HANDLERS.get(message_type)
