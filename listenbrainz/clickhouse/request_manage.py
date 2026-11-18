import click

from listenbrainz.clickhouse.jobs import add_job
from listenbrainz.webserver import create_app


cli = click.Group()


def send_request_to_clickhouse(query, **params):
    """Queue a persistent ClickHouse query job."""
    with create_app().app_context():
        add_job(query, params)

    click.echo(f"Request sent: {query}")


@cli.command(name="init_schema")
def init_schema():
    """Create the ClickHouse schema."""
    send_request_to_clickhouse("clickhouse.schema.init")


@cli.command(name="import_full_dump")
@click.option("--dump-id", type=click.IntRange(min=1), default=None, help="Import this full dump; defaults to the latest.")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
def import_full_dump(workers: int, dump_id: int | None):
    """Download a full dump from FTP and replace the ClickHouse listens."""
    send_request_to_clickhouse("clickhouse.import_full_dump", workers=workers, dump_id=dump_id)


@cli.command(name="import_incremental_dump")
@click.option("--dump-id", type=click.IntRange(min=1), default=None,
              help="Import only this incremental dump, requiring continuous coverage.")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
@click.option("--max-dumps", type=click.IntRange(min=1), default=None,
              help="Load at most this many dumps in one run; defaults to the whole backlog.")
def import_incremental_dump(workers: int, max_dumps: int | None, dump_id: int | None):
    """Import a selected incremental dump or catch up on all pending dumps."""
    if dump_id is not None and max_dumps is not None:
        raise click.UsageError("--dump-id and --max-dumps cannot be used together")
    send_request_to_clickhouse("clickhouse.import_incremental_dump", workers=workers, max_dumps=max_dumps, dump_id=dump_id)


if __name__ == '__main__':
    cli()
