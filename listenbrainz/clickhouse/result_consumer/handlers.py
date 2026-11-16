import logging


logger = logging.getLogger(__name__)


RESPONSE_HANDLERS = {}


def get_handler(message_type: str):
    """Get the handler function for a message type."""
    return RESPONSE_HANDLERS.get(message_type)
