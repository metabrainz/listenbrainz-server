import sys
import listenbrainz.utils as utils

import time
utils.safely_import_config()
from flask import current_app


class ListenWriter:
    def __init__(self):
        self.redis = None
        self.connection = None
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

        self.REPORT_FREQUENCY = 5000
        self.DUMP_JSON_WITH_ERRORS = False
        self.ERROR_RETRY_DELAY = 3 # number of seconds to wait until retrying an operation


    @staticmethod
    def static_callback(ch, method, properties, body, obj):
        return obj.callback(ch, method, properties, body)


    def connect_to_rabbitmq(self):
        connection_config = {
            'username': current_app.config['RABBITMQ_USERNAME'],
            'password': current_app.config['RABBITMQ_PASSWORD'],
            'host': current_app.config['RABBITMQ_HOST'],
            'port': current_app.config['RABBITMQ_PORT'],
            'virtual_host': current_app.config['RABBITMQ_VHOST'],
        }
        self.connection = utils.connect_to_rabbitmq(**connection_config,
                                                    error_logger=current_app.logger.error,
                                                    error_retry_delay=self.ERROR_RETRY_DELAY)

    def _collect_and_log_stats(self, count):
        self.inserts += count
        if self.inserts >= self.REPORT_FREQUENCY:
            self.total_inserts += self.inserts
            if self.time > 0:
                current_app.logger.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                    (self.inserts, self.time, count / self.time, self.total_inserts))
            self.inserts = 0
            self.time = 0


    def _verify_hosts_in_config(self):
        if "REDIS_HOST" not in current_app.config:
            current_app.logger.critical("Redis service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
            time.sleep(self.ERROR_RETRY_DELAY)
            sys.exit(-1)

        if "RABBITMQ_HOST" not in current_app.config:
            current_app.logger.critical("RabbitMQ service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
            time.sleep(self.ERROR_RETRY_DELAY)
            sys.exit(-1)
