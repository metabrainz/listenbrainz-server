"""
ClickHouse Analytics Module

This module provides ClickHouse-based analytics and stats functionality:
- Listen dump ingestion
- Incremental stats computation and caching
- Full and incremental dump loading

Components:
    - request_consumer: Consumes stats requests from CLICKHOUSE_EXCHANGE
    - request_manage: CLI commands for triggering ClickHouse operations
    - stats/: Stats computation and caching logic
"""
