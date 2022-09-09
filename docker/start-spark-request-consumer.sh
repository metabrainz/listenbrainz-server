#!/bin/bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")/../"

rm -rf pyspark_venv pyspark_venv.tar.gz listenbrainz_spark_request_consumer.zip models.zip

python3 -m venv pyspark_venv
source pyspark_venv/bin/activate
pip install -r requirements_spark.txt
pip install venv-pack
venv-pack -o pyspark_venv.tar.gz

export PYSPARK_DRIVER_PYTHON=python
export PYSPARK_PYTHON=./environment/bin/python

GIT_COMMIT_SHA="$(git describe --tags --dirty --always)"
echo "$GIT_COMMIT_SHA" > .git-version

zip -rq listenbrainz_spark_request_consumer.zip listenbrainz_spark/
zip -rq models.zip data/

source spark_config.sh
"${SPARK_HOME}"/bin/spark-submit \
        --master spark://leader:7077 \
        --archives "pyspark_venv.tar.gz#environment" \
        --conf "spark.cores.max=$MAX_CORES" \
        --executor-cores "$EXECUTOR_CORES" \
        --executor-memory "$EXECUTOR_MEMORY" \
        --driver-memory "$DRIVER_MEMORY" \
        --py-files listenbrainz_spark_request_consumer.zip,models.zip \
    spark_manage.py request_consumer
