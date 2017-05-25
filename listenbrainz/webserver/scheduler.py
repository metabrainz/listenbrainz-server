from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import sqlalchemy.exc
from apscheduler.schedulers.background import BackgroundScheduler
import logging

# Create a cron job to clean postgres database
class ScheduledJobs():
    """ Schedule the scripts that need to be run at scheduled intervals """

    def __init__(self, conf):
        self.conf = conf
        self.scheduler = BackgroundScheduler()
        self.add_jobs()
        self.run()

    def run(self):
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.shutdown()

    def add_jobs(self):
        args = {}
        if 'MAX_POSTGRES_LISTEN_HISTORY' in self.conf:
            args['max_days'] = int(self.conf['MAX_POSTGRES_LISTEN_HISTORY'])

        self.scheduler.add_job(self._clean_postgres, 'interval', hours=24, \
                kwargs=args)

    def _clean_postgres(self, max_days=90):
        """ Clean all the listens that are older than a set no of days
            Default: 90 days
        """

        # If max days is set to a negative number, don't throw anything out
        if max_days < 0:
            return

        seconds = max_days*24*3600
        engine = create_engine(self.conf['SQLALCHEMY_DATABASE_URI'], poolclass=NullPool)
        connection = engine.connect()
        # query = """
        #          WITH max_table as (
        #              SELECT user_id, max(extract(epoch from ts)) - %s as mx
        #              FROM listens
        #              GROUP BY user_id
        #          )
        #          DELETE FROM listens
        #          WHERE extract(epoch from ts) < (SELECT mx
        #                                          FROM max_table
        #                                          WHERE max_table.user_id = listens.user_id)
        #         RETURNING *
        #         """

        query = """
                DELETE FROM listen
                WHERE id in (
                    SELECT id FROM listen
                    JOIN (
                        SELECT user_id, extract(epoch from max(ts)) as max
                        FROM listens
                        GROUP BY user_id
                    ) max_table on listens.user_id = max_table.user_id AND extract(epoch from listens.ts) <= max_table.max - %s
                ) RETURNING *
                """

        deleted = connection.execute(query % (seconds))
        log = logging.getLogger(__name__)
        log.info('(Scheduled Job) CleanPostgres: ' + str(len(deleted.fetchall())) + " records deleted successfully")
        connection.close()

    def shutdown(self):
        self.scheduler.shutdown()
