from listenbrainz.manage import cli
import listenbrainz.db.dump_manager as dump_manager
import listenbrainz.spark.request_manage as spark_request_manage

# Add other commands here
cli.add_command(spark_request_manage.cli, name="spark")
cli.add_command(dump_manager.cli, name="dump")

if __name__ == '__main__':
    cli()
