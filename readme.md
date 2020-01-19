Note: We plan to archive this repository very soon. Please open all pull requests in
the [listenbrainz-server](https://github.com/metabrainz/listenbrainz-server) codebase.

Things to do in order for them to run correctly:
================================================

Set env var:

export PYSPARK_PYTHON=`which python3`


Install required modules:

pip3 install -r requirements.txt

Install java and scala:

apt-get install default-jdk scala

Install spark (download 2.3.0 tgz for hadoop and unzip in /usr/local/spark


To run the scripts:
===================

spark-submit --master spark://195.201.112.36:7077 --executor-memory=29g `pwd`/<script> <args>

spark-submit --master spark://195.201.112.36:7077 --executor-memory=29g `pwd`/train_models.py df models
