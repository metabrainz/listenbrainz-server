"""
ClickHouse Request Management

This module provides the client-side interface for sending ClickHouse
stats and management requests via RabbitMQ.

Components:
    - request_manage.py: CLI commands for sending requests
    - clickhouse_reader.py: consumes the result messages
    - handlers.py: handlers for the result messages

The actual request consumer and handlers run in the top-level clickhouse/
module, which is a separate worker process.
"""
