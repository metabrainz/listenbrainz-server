"""
ClickHouse Analytics Module

This module provides ClickHouse-based analytics and stats functionality:
- Listen dump ingestion
- Incremental stats computation and caching
- Full and incremental dump loading

Components:
    - request_consumer: Consumes stats requests from CLICKHOUSE_EXCHANGE
    - client: ClickHouse connection settings
    - stats/: Stats computation and caching logic

The CLI commands that send requests live in listenbrainz/clickhouse/request_manage.py.
"""
