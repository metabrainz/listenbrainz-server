import click
import orjson
from kombu import Connection, Exchange
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app


cli = click.Group()


def send_request_to_clickhouse(query, **params):
    """Send a request to the ClickHouse request queue."""
    app = create_app()
    with app.app_context():
        message = orjson.dumps({"query": query, "params": params})

        connection = Connection(
            hostname=app.config["RABBITMQ_HOST"],
            userid=app.config["RABBITMQ_USERNAME"],
            port=app.config["RABBITMQ_PORT"],
            password=app.config["RABBITMQ_PASSWORD"],
            virtual_host=app.config["RABBITMQ_VHOST"],
            transport_options={"client_properties": {"connection_name": get_fallback_connection_name()}}
        )

        clickhouse_exchange = Exchange(app.config.get("CLICKHOUSE_EXCHANGE", "clickhouse"), "fanout", durable=False)

        with connection.Producer() as producer:
            producer.publish(
                message,
                routing_key="",
                exchange=clickhouse_exchange,
                delivery_mode=PERSISTENT_DELIVERY_MODE,
                declare=[clickhouse_exchange]
            )

    click.echo(f"Request sent: {query}")


@cli.command(name="load_full_dump")
@click.option("--dump-path", required=True, help="Path to directory containing Parquet files")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
def load_full_dump(dump_path: str, workers: int):
    """Load a full Parquet dump into ClickHouse listens table."""
    send_request_to_clickhouse("clickhouse.load_full_dump", dump_path=dump_path, workers=workers)


@cli.command(name="load_incremental_dump")
@click.option("--dump-path", required=True, help="Path to directory containing Parquet files")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
def load_incremental_dump(dump_path: str, workers: int):
    """Load an incremental Parquet dump into ClickHouse listens table."""
    send_request_to_clickhouse("clickhouse.load_incremental_dump", dump_path=dump_path, workers=workers)


@cli.command(name="import_full_dump")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
def import_full_dump(workers: int):
    """Download latest full dump from FTP and import into ClickHouse."""
    send_request_to_clickhouse("clickhouse.import_full_dump", workers=workers)


@cli.command(name="import_incremental_dump")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
def import_incremental_dump(workers: int):
    """Download latest incremental dump from FTP and import into ClickHouse."""
    send_request_to_clickhouse("clickhouse.import_incremental_dump", workers=workers)


@cli.command(name="refresh_metadata_cache")
@click.option("--cache-type", "cache_types", multiple=True,
              type=click.Choice(["artist", "recording", "release", "release_group"]),
              help="Metadata cache type to refresh. May be passed multiple times; defaults to all.")
@click.option("--batch-size", type=int, default=100000, help="Rows to fetch from PostgreSQL per batch")
def refresh_metadata_cache(cache_types: tuple[str], batch_size: int):
    """Refresh ClickHouse MusicBrainz metadata cache tables."""
    send_request_to_clickhouse(
        "clickhouse.metadata_cache.refresh",
        cache_types=list(cache_types) or None,
        batch_size=batch_size,
    )


if __name__ == '__main__':
    cli()
