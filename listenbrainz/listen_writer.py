import logging
import listenbrainz.utils as utils

from listenbrainz import default_config as config
try:
    from listenbrainz import custom_config as config
except ImportError:
    pass

class ListenWriter:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.log.setLevel(logging.INFO)

        self.redis = None
        self.connection = None
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

        self.REPORT_FREQUENCY = 5000
        self.DUMP_JSON_WITH_ERRORS = False
        self.ERROR_RETRY_DELAY = 3 # number of seconds to wait until retrying an operation
        self.config = config


    @staticmethod
    def static_callback(ch, method, properties, body, obj):
        return obj.callback(ch, method, properties, body)


    def connect_to_rabbitmq(self):
        connection_config = {
            'username': self.config.RABBITMQ_USERNAME,
            'password': self.config.RABBITMQ_PASSWORD,
            'host': self.config.RABBITMQ_HOST,
            'port': self.config.RABBITMQ_PORT,
            'virtual_host': self.config.RABBITMQ_VHOST
        }
        self.connection = utils.connect_to_rabbitmq(**connection_config,
                                                    error_logger=self.log.error,
                                                    error_retry_delay=self.ERROR_RETRY_DELAY)


    def _collect_and_log_stats(self, count, call_method=lambda: None):
        self.inserts += count
        if self.inserts >= self.REPORT_FREQUENCY:
            self.total_inserts += self.inserts
            if self.time > 0:
                self.log.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                    (self.inserts, self.time, count / self.time, self.total_inserts))
            self.inserts = 0
            self.time = 0

            call_method()


    def _verify_hosts_in_config(self):
        if not hasattr(self.config, "REDIS_HOST"):
            self.log.error("Redis service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
            sleep(self.ERROR_RETRY_DELAY)
            sys.exit(-1)

        if not hasattr(self.config, "RABBITMQ_HOST"):
            self.log.error("RabbitMQ service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
            sleep(self.ERROR_RETRY_DELAY)
            sys.exit(-1)
