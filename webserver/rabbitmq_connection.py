import pika

_rabbitmq = None

def init_rabbitmq_connection(host, port):
    """Create a connection to the RabbitMQ server."""
    global _rabbitmq
    _rabbitmq = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
    return _rabbitmq
