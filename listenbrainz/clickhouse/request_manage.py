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

        clickhouse_exchange = Exchange(app.config["CLICKHOUSE_EXCHANGE"], "fanout", durable=True)

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


@cli.command(name="stats_hourly")
@click.option("--entity", type=click.Choice(['artist', 'recording', 'release_group']),
              help="Entity type to process (default: all)")
@click.option("--batch-size", type=int, default=1000, help="Number of users to process per batch")
def stats_hourly(entity: str, batch_size: int):
    """Run hourly stats cache refresh job."""
    send_request_to_clickhouse("clickhouse.stats.hourly", entity=entity, batch_size=batch_size)


@cli.command(name="stats_full_refresh")
@click.option("--entity", type=click.Choice(['artist', 'recording', 'release_group']),
              help="Entity type to process (default: all)")
@click.option("--batch-size", type=int, default=1000, help="Number of users to process per batch")
def stats_full_refresh(entity: str, batch_size: int):
    """Run full stats cache refresh for all users."""
    send_request_to_clickhouse("clickhouse.stats.full_refresh", entity=entity, batch_size=batch_size)


@cli.command(name="cleanup_deletions")
@click.option("--days", type=int, default=7, help="Number of days to retain processed deletions")
def cleanup_deletions(days: int):
    """Clean up processed deletions older than N days."""
    send_request_to_clickhouse("clickhouse.stats.cleanup_deletions", days=days)


@cli.command(name='cron_stats')
@click.pass_context
def cron_stats(ctx):
    """Cron job: run hourly refresh and cleanup old deletions."""
    ctx.invoke(stats_hourly)
    ctx.invoke(cleanup_deletions)


if __name__ == '__main__':
    cli()
