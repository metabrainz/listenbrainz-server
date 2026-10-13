import click
import orjson
from kombu import Exchange
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app


cli = click.Group()

CLICKHOUSE_ENTITY_TYPES = [
    "daily_activity",
    "listening_activity",
]


def send_request_to_clickhouse(query, **params):
    """Send a request to the ClickHouse request queue."""
    app = create_app()
    with app.app_context():
        message = orjson.dumps({"query": query, "params": params})

        connection = create_rabbitmq_connection(app.config)

        clickhouse_exchange = Exchange(app.config.get("CLICKHOUSE_EXCHANGE", "clickhouse"), "fanout", durable=True)

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


@cli.command(name="init_schema")
def init_schema():
    """Create the ClickHouse stats schema."""
    send_request_to_clickhouse("clickhouse.schema.init")


@cli.command(name="load_full_dump")
@click.option("--dump-path", required=True, help="Path to directory containing Parquet files")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
@click.option("--replace/--no-replace", default=True, show_default=True,
              help="Truncate listens and cache state before loading.")
def load_full_dump(dump_path: str, workers: int, replace: bool):
    """Load a full Parquet dump into ClickHouse listens table."""
    send_request_to_clickhouse("clickhouse.load_full_dump", dump_path=dump_path, workers=workers, replace=replace)


@cli.command(name="load_incremental_dump")
@click.option("--dump-path", required=True, help="Path to directory containing Parquet files")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
def load_incremental_dump(dump_path: str, workers: int):
    """Load an incremental Parquet dump into ClickHouse listens table."""
    send_request_to_clickhouse("clickhouse.load_incremental_dump", dump_path=dump_path, workers=workers)


@cli.command(name="import_full_dump")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
@click.option("--replace/--no-replace", default=True, show_default=True,
              help="Truncate listens and cache state before loading.")
def import_full_dump(workers: int, replace: bool):
    """Download latest full dump from FTP and import into ClickHouse."""
    send_request_to_clickhouse("clickhouse.import_full_dump", workers=workers, replace=replace)


@cli.command(name="record_imported_dump")
@click.option("--dump-id", type=int, required=True, help="Id of the dump that is already in listens")
@click.option("--dump-type", type=click.Choice(["full", "incremental"]), required=True)
@click.option("--imported-at", default=None,
              help="When it was loaded, as UTC 'YYYY-MM-DD HH:MM:SS[.mmm]'; defaults to now. "
                   "A dump loaded before the latest full dump import needs its real timestamp.")
def record_imported_dump(dump_id: int, dump_type: str, imported_at: str):
    """Record a dump as already loaded, without loading it.

    Seeds imported_dumps for dumps that went into listens before that table existed, so
    import_incremental_dump resumes from the right place instead of treating every dump
    on the FTP server as missing.
    """
    send_request_to_clickhouse(
        "clickhouse.record_imported_dump",
        dump_id=dump_id, dump_type=dump_type, imported_at=imported_at,
    )


@cli.command(name="import_deleted_listens")
@click.option("--batch-size", type=int, default=10000, help="Rows to fetch from the listens database per batch")
def import_deleted_listens(batch_size: int):
    """Import listen deletions from the listens database and apply them to ClickHouse listens and stats."""
    send_request_to_clickhouse("clickhouse.import_deleted_listens", batch_size=batch_size)


@cli.command(name="import_incremental_dump")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
@click.option("--max-dumps", type=int, default=None,
              help="Load at most this many dumps in one run; defaults to the whole backlog.")
def import_incremental_dump(workers: int, max_dumps: int):
    """Import every incremental dump on FTP that ClickHouse has not loaded yet."""
    send_request_to_clickhouse("clickhouse.import_incremental_dump", workers=workers, max_dumps=max_dumps)


@cli.command(name="request_hourly_stats")
@click.option("--entity", "entities", multiple=True, type=click.Choice(CLICKHOUSE_ENTITY_TYPES),
              help="Stat type to refresh. May be passed multiple times; defaults to all.")
@click.option("--batch-size", type=int, default=1000, help="Users to process per ClickHouse query batch")
def request_hourly_stats(entities: tuple[str], batch_size: int):
    """Request an incremental ClickHouse user stats refresh."""
    _send_stats_request("clickhouse.stats.hourly", entities, batch_size)


@cli.command(name="request_full_stats_refresh")
@click.option("--entity", "entities", multiple=True, type=click.Choice(CLICKHOUSE_ENTITY_TYPES),
              help="Stat type to refresh. May be passed multiple times; defaults to all.")
@click.option("--message-batch-size", type=int, default=100,
              help="Users per outbound RMQ message.")
@click.option("--user-flush-size", type=int, default=5000,
              help="Users buffered from the ClickHouse stream before messages are emitted.")
def request_full_stats_refresh(entities: tuple[str], message_batch_size: int, user_flush_size: int):
    """Request a full ClickHouse user stats refresh."""
    params = {"message_batch_size": message_batch_size, "user_flush_size": user_flush_size}
    if not entities:
        send_request_to_clickhouse("clickhouse.stats.full_refresh", **params)
        return
    for entity in entities:
        send_request_to_clickhouse("clickhouse.stats.full_refresh", entity=entity, **params)


@cli.command(name="cron_request_all_stats")
@click.option("--stats-batch-size", type=int, default=1000, help="Users to process per ClickHouse query batch")
@click.pass_context
def cron_request_all_stats(ctx, stats_batch_size: int):
    """Request an incremental refresh of every ClickHouse user stat."""
    ctx.invoke(request_hourly_stats, entities=(), batch_size=stats_batch_size)


if __name__ == '__main__':
    cli()
