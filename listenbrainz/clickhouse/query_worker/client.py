"""ClickHouse connection settings."""

from dataclasses import dataclass

import clickhouse_connect
from clickhouse_connect.driver import Client
from flask import current_app


@dataclass(frozen=True)
class ClickHouseConnection:
    """Where to connect to: the configured server, or a test database in tests."""
    host: str
    port: int
    username: str
    password: str
    database: str

    @classmethod
    def from_config(cls) -> "ClickHouseConnection":
        return cls(
            host=current_app.config["CLICKHOUSE_HOST"],
            port=current_app.config["CLICKHOUSE_PORT"],
            username=current_app.config["CLICKHOUSE_USERNAME"],
            password=current_app.config["CLICKHOUSE_PASSWORD"],
            database=current_app.config["CLICKHOUSE_DATABASE"],
        )

    def connect(self, **kwargs) -> Client:
        """Open a client without a session: a session runs one query at a time, so a query
        left running by a client timeout would lock it for the client's next query.
        ``kwargs`` are passed on to ``clickhouse_connect.get_client``."""
        return clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            database=self.database,
            autogenerate_session_id=False,
            **kwargs,
        )
