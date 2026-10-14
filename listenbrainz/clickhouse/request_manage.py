import click

from listenbrainz.clickhouse.jobs import add_job
from listenbrainz.webserver import create_app


cli = click.Group()


def send_request_to_clickhouse(query, **params):
    """Queue a persistent ClickHouse query job."""
    with create_app().app_context():
        add_job(query, params)

    click.echo(f"Request sent: {query}")


if __name__ == '__main__':
    cli()
