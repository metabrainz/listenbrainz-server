import click
import orjson
from kombu import Exchange
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.clickhouse.handlers import ENTITY_MODELS
from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app


cli = click.Group()

CLICKHOUSE_ENTITY_TYPES = list(ENTITY_MODELS)


def send_request_to_clickhouse(query, **params):
    """Send a request to the ClickHouse request queue."""
    app = create_app()
    message = orjson.dumps({"query": query, "params": params})
    clickhouse_exchange = Exchange(app.config["CLICKHOUSE_EXCHANGE"], "fanout", durable=True)
    with app.app_context(), create_rabbitmq_connection(app.config) as connection:
        with connection.Producer() as producer:
            producer.publish(
                message,
                routing_key="",
                exchange=clickhouse_exchange,
                delivery_mode=PERSISTENT_DELIVERY_MODE,
                declare=[clickhouse_exchange]
            )

    click.echo(f"Request sent: {query}")


def _send_stats_request(query: str, entities: tuple[str], **params):
    """Send one ClickHouse stats request, or one per selected entity."""
    if not entities:
        send_request_to_clickhouse(query, **params)
        return

    for entity in entities:
        send_request_to_clickhouse(query, entity=entity, **params)


@cli.command(name="init_schema")
def init_schema():
    """Create the ClickHouse stats schema."""
    send_request_to_clickhouse("clickhouse.schema.init")


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


@cli.command(name="set_dump_import_state")
@click.option("--dump-id", type=int, required=True, help="Id of the last dump already in listens")
def set_dump_import_state(dump_id: int):
    """Set the incremental dump mark, so that import_incremental_dump loads the dumps after it."""
    send_request_to_clickhouse("clickhouse.set_dump_import_state", dump_id=dump_id)


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
    _send_stats_request("clickhouse.stats.hourly", entities, batch_size=batch_size)


@cli.command(name="request_full_stats_refresh")
@click.option("--entity", "entities", multiple=True, type=click.Choice(CLICKHOUSE_ENTITY_TYPES),
              help="Stat type to refresh. May be passed multiple times; defaults to all.")
@click.option("--message-batch-size", type=int, default=100,
              help="Users per outbound RMQ message.")
@click.option("--user-flush-size", type=int, default=5000,
              help="Users buffered from the ClickHouse stream before messages are emitted.")
def request_full_stats_refresh(entities: tuple[str], message_batch_size: int, user_flush_size: int):
    """Request a full ClickHouse user stats refresh."""
    _send_stats_request(
        "clickhouse.stats.full_refresh", entities,
        message_batch_size=message_batch_size, user_flush_size=user_flush_size,
    )


@cli.command(name="cron_request_all_stats")
@click.option("--stats-batch-size", type=int, default=1000, help="Users to process per ClickHouse query batch")
@click.pass_context
def cron_request_all_stats(ctx, stats_batch_size: int):
    """Request an incremental refresh of every ClickHouse user stat."""
    ctx.invoke(request_hourly_stats, entities=(), batch_size=stats_batch_size)


if __name__ == '__main__':
    cli()
