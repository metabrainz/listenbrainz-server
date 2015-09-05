from kafka import KafkaClient

_kafka = None

def init_kafka_connection(connect_string):
    global _kafka

    # Create a connection to the Kafka server
    _kafka = KafkaClient(connect_string)
