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
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
def import_full_dump(workers: int):
    """Download latest full dump from FTP and import into ClickHouse."""
    send_request_to_clickhouse("clickhouse.import_full_dump", workers=workers)


@cli.command(name="import_incremental_dump")
@click.option("--workers", type=int, default=4, help="Number of parallel workers for loading")
@click.option("--max-dumps", type=click.IntRange(min=1), default=None,
              help="Load at most this many dumps in one run; defaults to the whole backlog.")
def import_incremental_dump(workers: int, max_dumps: int):
    """Import every incremental dump on FTP that ClickHouse has not loaded yet."""
    send_request_to_clickhouse("clickhouse.import_incremental_dump", workers=workers, max_dumps=max_dumps)


if __name__ == '__main__':
    cli()
