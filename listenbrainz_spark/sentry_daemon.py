import sentry_sdk
from sentry_sdk.integrations.spark import SparkWorkerIntegration
import pyspark.daemon as original_daemon

import listenbrainz_spark.config as conf

if __name__ == '__main__':
    sentry_sdk.init(**conf.LOG_SENTRY, integrations=[SparkWorkerIntegration()])
    original_daemon.manager()
