import sys
import time

from flask import current_app

import listenbrainz.utils as utils


class ListenWriter:
    def __init__(self):
        self.redis = None
        self.connection = None

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

    def _verify_hosts_in_config(self):
        if "REDIS_HOST" not in current_app.config:
            current_app.logger.critical("Redis service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
            time.sleep(self.ERROR_RETRY_DELAY)
            sys.exit(-1)

        if "RABBITMQ_HOST" not in current_app.config:
            current_app.logger.critical("RabbitMQ service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
            time.sleep(self.ERROR_RETRY_DELAY)
            sys.exit(-1)
