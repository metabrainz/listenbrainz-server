"""ClickHouse connection settings shared by the stats pipeline."""

from dataclasses import dataclass

import clickhouse_connect
from clickhouse_connect.driver import Client

from clickhouse import config


@dataclass(frozen=True)
class ClickHouseConnection:
    """Where to connect to: the configured server by default, a test database in tests."""
    host: str = "localhost"
    port: int = 8123
    username: str = "default"
    password: str = ""
    database: str = "default"

    @classmethod
    def from_config(cls) -> "ClickHouseConnection":
        return cls(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            username=config.CLICKHOUSE_USERNAME,
            password=config.CLICKHOUSE_PASSWORD,
            database=config.CLICKHOUSE_DATABASE,
        )

    def connect(self, **kwargs) -> Client:
        """Open a client; ``kwargs`` are passed on to ``clickhouse_connect.get_client``."""
        return clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            database=self.database,
            **kwargs,
        )
