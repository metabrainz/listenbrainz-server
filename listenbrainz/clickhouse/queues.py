"""RabbitMQ exchanges and queues of the ClickHouse stats pipeline."""

from kombu import Exchange, Queue


CLICKHOUSE_RESULT_EXCHANGE: Exchange | None = None
CLICKHOUSE_RESULT_QUEUE: Queue | None = None


def init_queues(config):
    """Initialize the ClickHouse exchanges and queues from the config."""
    global CLICKHOUSE_RESULT_EXCHANGE, CLICKHOUSE_RESULT_QUEUE
    CLICKHOUSE_RESULT_EXCHANGE = Exchange(config["CLICKHOUSE_RESULT_EXCHANGE"], "fanout", durable=True)
    CLICKHOUSE_RESULT_QUEUE = Queue(
        config["CLICKHOUSE_RESULT_QUEUE"],
        exchange=CLICKHOUSE_RESULT_EXCHANGE,
        durable=True,
    )
