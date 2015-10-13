import kafka
from flask import current_app

def get_kafka_client():
    """Create a connection to the Kafka server."""
    host = current_app.config['KAFKA_CONNECT']
    return kafka.KafkaClient(host)
