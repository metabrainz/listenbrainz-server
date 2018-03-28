Things to do in order for them to run correctly:

Set env var:

export PYSPARK_PYTHON=`which python3`

Install required modules:

pip3 install -r requirements.txt


invoke with:

spark-submit --driver-memory 1g lb-recommendation.py data/top_listens_2017_by_user.json data/top_listens_2017_recording_id.json data/top_listens_2017_user_rob.json
