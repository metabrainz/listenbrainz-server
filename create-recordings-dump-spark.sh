#!/bin/bash

echo 'This script is run by the following user: '; whoami

./spark-submit.sh spark_manage.py dataframe
./spark-submit.sh spark_manage.py model
./spark-submit.sh spark_manage.py candidate
./spark-submit.sh spark_manage.py recommend --create_dump
