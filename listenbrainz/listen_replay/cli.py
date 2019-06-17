import click


from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from listenbrainz.listen_replay.demo import DemoUserReplayer


cli = click.Group()


@cli.command(name="demo_user_replay")
@click.argument("user_name", type=str)
def demo_user_replay(user_name):
    replayer = DemoUserReplayer(user_name)
    try:
        replayer.start()
    except (InfluxDBClientError, InfluxDBServerError) as e:
        replayer.app.logger.error("Influx error while replaying listens: %s", str(e), exc_info=True)
        raise
    except Exception as e:
        replayer.app.logger.error("Error while replaying listens: %s", str(e), exc_info=True)
        raise

# add more commands here as needed
