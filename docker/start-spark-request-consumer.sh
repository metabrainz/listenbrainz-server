#!/bin/bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")/../"

rm -rf pyspark_venv pyspark_venv.tar.gz listenbrainz_spark_request_consumer.zip models.zip

python3.13 -m venv pyspark_venv
source pyspark_venv/bin/activate
pip install --upgrade pip setuptools wheel venv-pack -r requirements_spark.txt
venv-pack -o pyspark_venv.tar.gz

VENV_PATH="$(realpath pyspark_venv)"
export PYSPARK_DRIVER_PYTHON="${VENV_PATH}/bin/python3.13"
export PYSPARK_PYTHON=./environment/bin/python3.13

GIT_COMMIT_SHA="$(git describe --tags --dirty --always)"
echo "$GIT_COMMIT_SHA" > .git-version

zip -rq listenbrainz_spark_request_consumer.zip listenbrainz_spark/
zip -rq models.zip data/

source spark_config.sh
"${SPARK_HOME}"/bin/spark-submit \
        --master spark://leader:7077 \
        --archives "pyspark_venv.tar.gz#environment" \
        --conf "spark.cores.max=$MAX_CORES" \
        --conf "spark.driver.maxResultSize=$DRIVER_MAX_RESULT_SIZE" \
        --executor-cores "$EXECUTOR_CORES" \
        --executor-memory "$EXECUTOR_MEMORY" \
        --driver-memory "$DRIVER_MEMORY" \
        --py-files listenbrainz_spark_request_consumer.zip,models.zip \
        spark_manage.py
