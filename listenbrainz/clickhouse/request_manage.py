import click
import orjson
from kombu import Exchange
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app


cli = click.Group()


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


if __name__ == '__main__':
    cli()
