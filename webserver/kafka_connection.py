from kafka import KafkaClient

_kafka = None


def init_kafka_connection(hosts):
    """Create a connection to the Kafka server."""
    global _kafka
    _kafka = KafkaClient(hosts)
