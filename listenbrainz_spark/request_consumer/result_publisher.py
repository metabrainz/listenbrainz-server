import functools
import json
import logging
import time

import pika

from listenbrainz_spark import config

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


def get_result_channel(connection):
    result_channel = connection.channel()
    result_channel.exchange_declare(
        exchange=config.SPARK_RESULT_EXCHANGE,
        exchange_type='fanout'
    )
    return result_channel


def invoke_query(
        connection,
        request_channel,
        delivery_tag,
        query_handler,
        params
    ):
    t0 = time.monotonic()
    messages = get_results(query_handler, params)
    if messages is None:
        return

    result_channel = get_result_channel(connection)

    logger.info("Pushing result to RabbitMQ...")
    num_of_messages = 0
    avg_size_of_message = 0

    for message in messages:
        num_of_messages += 1
        body = json.dumps(message)
        avg_size_of_message += len(body)
        while message is not None:
            try:
                result_channel.basic_publish(
                    exchange=config.SPARK_RESULT_EXCHANGE,
                    routing_key='',
                    body=body,
                    properties=pika.BasicProperties(delivery_mode=2, ),
                )
                break
            # we do not catch ConnectionClosed exception here because when
            # a connection closes so do all of the channels on it. so if the
            # connection is closed, we have lost the request channel. hence,
            # we'll be unable to ack the request later and receive it again
            # for processing anyways.
            except pika.exceptions.ChannelClosed:
                logger.error('RabbitMQ Connection error while publishing results:', exc_info=True)
                time.sleep(1)
                result_channel = get_result_channel(connection)

    try:
        avg_size_of_message //= num_of_messages
    except ZeroDivisionError:
        avg_size_of_message = 0
        logger.warning("No messages calculated", exc_info=True)

    logger.info("Done!")
    logger.info("Number of messages sent: {}".format(num_of_messages))
    logger.info("Average size of message: {} bytes".format(avg_size_of_message))

    logger.info("Time Taken: %d s", time.monotonic() - t0)
    callback = functools.partial(request_channel.basic_ack, delivery_tag)
    connection.add_callback_threadsafe(callback)
