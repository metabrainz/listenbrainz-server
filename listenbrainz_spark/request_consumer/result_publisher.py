import functools
import json
import logging
import time

logger = logging.getLogger(__name__)


def get_results(query_handler, params):
    try:
        return query_handler(**params)
    except TypeError:
        logger.error("TypeError in the query handler for query '%s', "
                     "maybe bad params: ", query_handler, exc_info=True)
        return None
    except Exception:
        logger.error("Error in the query handler for query '%s':",
                     query_handler, exc_info=True)
        return None


def invoke_query(connection, channel, delivery_tag,
                 query_handler, params, method_to_callback):
    t0 = time.monotonic()
    messages = get_results(query_handler, params)
    if messages is None:
        ack_callback = functools.partial(channel.basic_ack, delivery_tag)
        connection.add_callback_threadsafe(ack_callback)
        return

    logger.info("Pushing result to RabbitMQ...")
    num_of_messages = 0
    avg_size_of_message = 0
    list_of_messages = list()

    for message in messages:
        if message is None:
            continue
        num_of_messages += 1
        body = json.dumps(message)
        avg_size_of_message += len(body)
        list_of_messages.append(body)

    callback = functools.partial(method_to_callback, list_of_messages)
    connection.add_callback_threadsafe(callback)

    ack_callback = functools.partial(channel.basic_ack, delivery_tag)
    connection.add_callback_threadsafe(ack_callback)

    try:
        avg_size_of_message //= num_of_messages
    except ZeroDivisionError:
        avg_size_of_message = 0
        logger.warning("No messages calculated", exc_info=True)

    logger.info("Number of messages sent: {}".format(num_of_messages))
    logger.info("Average size of message: {} bytes".format(avg_size_of_message))
    logger.info("Time Taken: %d s", time.monotonic() - t0)
    logger.info('Request done!')
