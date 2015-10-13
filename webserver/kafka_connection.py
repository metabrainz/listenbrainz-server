import kafka

def init_kafka_connection(hosts):
    """Create a connection to the Kafka server."""
    return kafka.KafkaClient(hosts)
