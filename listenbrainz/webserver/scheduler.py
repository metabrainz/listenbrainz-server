""" This module contains code that triggers jobs we want to run
    on regular intervals.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from listenbrainz.stats.calculate import calculate_stats

class ScheduledJobs():
    """Schedule the scripts that need to be run at regular intervals """

    def __init__(self, conf):
        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.log.setLevel(logging.INFO)

        self.conf = conf
        self.scheduler = BackgroundScheduler()
        self.add_jobs()
        self.run()

    def run(self):
        """ Start the scheduler but stop on KeyboardInterrupts and such"""
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()

    def add_jobs(self):
        """Add the jobs that need to be run to the scheduler"""
        self.scheduler.add_job(calculate_stats, 'interval', days=self.conf['STATS_CALCULATION_INTERVAL'])
