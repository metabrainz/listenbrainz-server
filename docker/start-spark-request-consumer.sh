#!/bin/bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")/../"

rm -rf pyspark_venv pyspark_venv.tar.gz listenbrainz_spark_request_consumer.zip models.zip

python3.13 -m venv pyspark_venv
source pyspark_venv/bin/activate
pip install --no-cache-dir --no-deps --upgrade "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
pip install --upgrade setuptools wheel venv-pack -r requirements_spark.txt
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
