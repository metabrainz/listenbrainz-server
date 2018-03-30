Things to do in order for them to run correctly:
================================================

Set env var:

export PYSPARK_PYTHON=`which python3`


Install required modules:

pip3 install -r requirements.txt

Install java and scala:

apt-get install default-jdk scala

Install spark (download 2.3.0 tgz for hadoop and unzip in /usr/local/spark


To run the script:
==================

spark-submit --driver-memory 15g lb-recommendation.py data/listens_2017_playcounts.json listens_2017_recording_id.json user_playcounts_rob.json

