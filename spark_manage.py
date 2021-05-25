import click
import logging
import time


@click.group()
def cli():
    pass


@cli.command(name='request_consumer')
def request_consumer():
    """ Invoke script responsible for the request consumer
    """
    from listenbrainz_spark.request_consumer.request_consumer import main
    main('request-consumer-%s' % str(int(time.time())))


if __name__ == '__main__':
    # The root logger always defaults to WARNING level
    # The level is changed from WARNING to INFO
    logging.getLogger().setLevel(logging.INFO)
    cli()
