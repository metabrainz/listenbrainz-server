from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import sqlalchemy.exc

from apscheduler.schedulers.background import BackgroundScheduler

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
        self.scheduler.add_job(self._clean_postgres, 'interval', hours=24)

    def _clean_postgres(self):
        """ Clean all the listens that are older than 90 days """
        max_days = 90
        seconds = 90*24*3600
        engine = create_engine(self.conf['SQLALCHEMY_DATABASE_URI'], poolclass=NullPool)
        connection = engine.connect()
        query = """
                 WITH max_table as (
                     SELECT uid, max(timestamp) - %s as mx
                     FROM listens
                     GROUP BY uid
                 )
                 DELETE FROM listens
                 WHERE timestamp < (SELECT mx
                                    FROM max_table
                                    WHERE max_table.uid = listens.uid);
                """
        connection.execute(query % (seconds))
        connection.close()

    def shutdown(self):
        self.scheduler.shutdown()
