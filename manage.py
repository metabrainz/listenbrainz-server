import listenbrainz.spark.request_manage as spark_request_manage
from listenbrainz.dumps import manager as dump_manager
from listenbrainz.listenstore import migrate_listens
from listenbrainz.manage import cli

# Add other commands here
cli.add_command(spark_request_manage.cli, name="spark")
cli.add_command(dump_manager.cli, name="dump")
cli.add_command(migrate_listens.cli, name="migrate_listens")

if __name__ == '__main__':
    cli()
