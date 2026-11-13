"""Replay rejected listen batches without requiring RabbitMQ plugins."""

import click
from flask import current_app
from kombu import Producer, Queue

from listenbrainz.rabbitmq import create_rabbitmq_connection

BATCH_SIZE = 100


def replay_rejected_listens(max_messages=None, dry_run=False):
    source = current_app.config["REJECTION_QUEUE"]
    target = current_app.config["INCOMING_QUEUE"]
    if source == target:
        raise click.ClickException("Rejection and incoming queues must differ.")

    def unroutable(*args):
        raise click.ClickException("Message could not be routed; source message was not acknowledged.")

    with create_rabbitmq_connection(
        current_app.config, transport_options={"confirm_publish": True}
    ) as connection, connection.channel() as channel:
        # Passive declarations do not create queues or change their type/bindings.
        channel.queue_declare(queue=target, passive=True)
        _, count, _ = channel.queue_declare(queue=source, passive=True)
        limit = count if max_messages is None else min(count, max_messages)
        click.echo(f"{source}: {count} ready messages; replay limit: {limit}.")
        if dry_run:
            return 0

        queue = Queue(source, channel=channel, no_declare=True)
        producer = Producer(channel, auto_declare=False, on_return=unroutable)
        moved = 0
        # Capture the initial count, rather than draining indefinitely while the
        # writer may return failed messages to rejection.
        while moved < limit:
            batch = []
            for _ in range(min(BATCH_SIZE, limit - moved)):
                message = queue.get(no_ack=False)
                if message is None:
                    break
                batch.append(message)
            if not batch:
                break
            # The writer reads raw JSON bytes. Avoid JSON-encoding the payload
            # again or forwarding compression headers for a decoded body.
            for message in batch:
                body = message.body
                if isinstance(body, str):
                    body = body.encode("utf-8")
                producer.publish(
                    body,
                    exchange="",
                    routing_key=target,
                    content_type="application/octet-stream",
                    content_encoding="binary",
                    delivery_mode=2,
                    mandatory=True,
                    retry=False,
                    confirm_timeout=30,
                )
            # This channel consumes only rejection messages. Acknowledge the
            # entire batch after every publication has been confirmed. On failure,
            # channel closure requeues the whole unacknowledged batch.
            batch[-1].ack(multiple=True)
            moved += len(batch)
            current_app.logger.info(f"Replayed {moved}/{limit} messages.")
        current_app.logger.info(f"Replayed {moved} messages to {target}.")
        return moved
