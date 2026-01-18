"""
ClickHouse Request Management

This module provides the client-side interface for sending ClickHouse
stats and management requests via RabbitMQ.

Components:
    - request_manage.py: CLI commands for sending requests
    - request_queries.json: Query definitions with parameters

The actual request consumer and handlers run in the top-level clickhouse/
module, which is a separate worker process.
"""
