#!/bin/bash

source spark_config.sh

zip -r listenbrainz_spark.zip listenbrainz_spark/
time ./run.sh /usr/local/spark/bin/spark-submit \
	--packages org.apache.spark:spark-avro_2.11:2.4.1 \
	--master $SPARK_URI \
	--conf "spark.scheduler.listenerbus.eventqueue.capacity"=$LISTENERBUS_CAPACITY \
  --conf "spark.cores.max"=$MAX_CORES \
  --conf "spark.executor.cores"=$EXECUTOR_CORES \
  --conf "spark.executor.memory"=$EXECUTOR_MEMORY \
  --conf "spark.driver.memory"=$DRIVER_MEMORY \
  --conf "spark.driver.memoryOverhead"=$DRIVER_MEMORY_OVERHEAD \
  --conf "spark.executor.memoryOverhead"=$EXECUTOR_MEMORY_OVERHEAD \
	--conf "spark.driver.maxResultSize"=$DRIVER_MAX_RESULT_SIZE \
	--conf "spark.python.use.daemon"=true \
  --conf "spark.python.daemon.module"=sentry_daemon \
	--py-files listenbrainz_spark.zip \
	"$@"
