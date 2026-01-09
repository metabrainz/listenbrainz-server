import listenbrainz.spark.request_manage as spark_request_manage
from listenbrainz.dumps import manager as dump_manager
from listenbrainz.manage import cli


cli.add_command(spark_request_manage.cli, name="spark")
cli.add_command(dump_manager.cli, name="dump")

if __name__ == '__main__':
    cli()
