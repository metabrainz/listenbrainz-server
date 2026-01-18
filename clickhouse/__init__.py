"""
ClickHouse Analytics Module

This module provides ClickHouse-based analytics and stats functionality:
- Real-time listen ingestion from RabbitMQ
- Incremental stats computation and caching
- Full and incremental dump loading

Components:
    - listen_consumer: Consumes listens from UNIQUE_EXCHANGE and inserts into ClickHouse
    - request_consumer: Consumes stats requests from CLICKHOUSE_EXCHANGE
    - request_manage: CLI commands for triggering ClickHouse operations
    - stats/: Stats computation and caching logic
"""
