#!/bin/bash

echo 'This script is run by the following user: '; whoami

./spark-submit.sh spark_manage.py dataframe
./spark_submit.sh spark_submit.py model
./spark_submit.sh spark_manage.py candidate
./spark_submit.sh spark_manage.py recommend --create_dump
