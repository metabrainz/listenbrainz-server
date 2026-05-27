import click
import orjson
from kombu import Connection, Exchange
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app


cli = click.Group()

CLICKHOUSE_ENTITY_TYPES = ["artists", "recordings", "release_groups"]


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


def _send_stats_request(query: str, entities: tuple[str], batch_size: int):
    """Send one ClickHouse stats request, or one per selected entity."""
    if not entities:
        send_request_to_clickhouse(query, batch_size=batch_size)
        return

    for entity in entities:
        send_request_to_clickhouse(query, entity=entity, batch_size=batch_size)


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


@cli.command(name="request_hourly_stats")
@click.option("--entity", "entities", multiple=True, type=click.Choice(CLICKHOUSE_ENTITY_TYPES),
              help="Entity stats to refresh. May be passed multiple times; defaults to all.")
@click.option("--batch-size", type=int, default=1000, help="Users to process per ClickHouse query batch")
def request_hourly_stats(entities: tuple[str], batch_size: int):
    """Request an incremental ClickHouse user entity stats refresh."""
    _send_stats_request("clickhouse.stats.hourly", entities, batch_size)


@cli.command(name="request_full_stats_refresh")
@click.option("--entity", "entities", multiple=True, type=click.Choice(CLICKHOUSE_ENTITY_TYPES),
              help="Entity stats to refresh. May be passed multiple times; defaults to all.")
@click.option("--batch-size", type=int, default=1000, help="Users to process per ClickHouse query batch")
def request_full_stats_refresh(entities: tuple[str], batch_size: int):
    """Request a full ClickHouse user entity stats refresh."""
    _send_stats_request("clickhouse.stats.full_refresh", entities, batch_size)


@cli.command(name="request_bulk_full_stats_refresh")
@click.option("--entity", "entities", multiple=True, type=click.Choice(CLICKHOUSE_ENTITY_TYPES),
              help="Entity stats to refresh. May be passed multiple times; defaults to all.")
@click.option("--message-batch-size", type=int, default=100,
              help="Users per outbound RMQ message.")
@click.option("--user-flush-size", type=int, default=5000,
              help="Users buffered from the ClickHouse stream before messages are emitted.")
def request_bulk_full_stats_refresh(entities: tuple[str], message_batch_size: int, user_flush_size: int):
    """Request a bulk ClickHouse user entity stats refresh (single intermediate scan)."""
    params = {"message_batch_size": message_batch_size, "user_flush_size": user_flush_size}
    if not entities:
        send_request_to_clickhouse("clickhouse.stats.bulk_full_refresh", **params)
        return
    for entity in entities:
        send_request_to_clickhouse("clickhouse.stats.bulk_full_refresh", entity=entity, **params)


@cli.command(name="refresh_metadata_cache")
@click.option("--cache-type", "cache_types", multiple=True,
              type=click.Choice(["artist", "recording", "release", "release_group"]),
              help="Metadata cache type to refresh. May be passed multiple times; defaults to all.")
@click.option("--batch-size", type=int, default=100000, help="Rows to fetch from PostgreSQL per batch")
@click.option("--max-retries", type=int, default=2, help="Retries per cache after a PostgreSQL connection failure")
def refresh_metadata_cache(cache_types: tuple[str], batch_size: int, max_retries: int):
    """Refresh ClickHouse MusicBrainz metadata cache tables."""
    send_request_to_clickhouse(
        "clickhouse.metadata_cache.refresh",
        cache_types=list(cache_types) or None,
        batch_size=batch_size,
        max_retries=max_retries,
    )


@cli.command(name="cron_request_all_stats")
@click.option("--stats-batch-size", type=int, default=1000, help="Users to process per ClickHouse query batch")
@click.option("--metadata-batch-size", type=int, default=100000, help="Rows to fetch from PostgreSQL per metadata batch")
@click.option("--metadata-max-retries", type=int, default=2,
              help="Retries per metadata cache after a PostgreSQL connection failure")
@click.pass_context
def cron_request_all_stats(ctx, stats_batch_size: int, metadata_batch_size: int, metadata_max_retries: int):
    """Request metadata refresh and incremental ClickHouse stats refresh."""
    ctx.invoke(refresh_metadata_cache, cache_types=(), batch_size=metadata_batch_size, max_retries=metadata_max_retries)
    ctx.invoke(request_hourly_stats, entities=(), batch_size=stats_batch_size)


@cli.command(name="cron_request_full_stats_refresh")
@click.option("--stats-batch-size", type=int, default=1000, help="Users to process per ClickHouse query batch")
@click.option("--metadata-batch-size", type=int, default=100000, help="Rows to fetch from PostgreSQL per metadata batch")
@click.option("--metadata-max-retries", type=int, default=2,
              help="Retries per metadata cache after a PostgreSQL connection failure")
@click.pass_context
def cron_request_full_stats_refresh(ctx, stats_batch_size: int, metadata_batch_size: int, metadata_max_retries: int):
    """Request metadata refresh and full ClickHouse stats refresh."""
    ctx.invoke(refresh_metadata_cache, cache_types=(), batch_size=metadata_batch_size, max_retries=metadata_max_retries)
    ctx.invoke(request_full_stats_refresh, entities=(), batch_size=stats_batch_size)


if __name__ == '__main__':
    cli()
