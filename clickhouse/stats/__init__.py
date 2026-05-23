"""
ClickHouse Stats Module

Provides stats computation functionality:
- cache_manager: Computes entity stats and emits RabbitMQ result messages
- load_dump: Loads Parquet dumps into ClickHouse
- handlers: Query handlers for stats operations
"""
