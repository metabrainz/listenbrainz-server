"""
ClickHouse Stats Module

Provides stats computation functionality:
- cache_manager: Shared stats cache state / RabbitMQ result message machinery
- activity_cache_manager: Computes daily and listening activity stats
- load_dump: Loads Parquet dumps into ClickHouse
- deleted_listens: Applies ListenBrainz listen deletions to ClickHouse
- handlers: Query handlers for stats operations
"""
