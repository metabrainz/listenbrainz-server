import time

from listenbrainz_spark.request_consumer.request_consumer import RequestConsumer


if __name__ == "__main__":
    app_name = f"request-consumer-{int(time.time())}"
    rc = RequestConsumer()
    rc.start(app_name)
