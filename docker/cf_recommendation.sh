#!/bin/bash

function invoke_cf_recommendation_scripts {
    /usr/local/bin/python /code/listenbrainz/manage.py spark request_dataframes
    /usr/local/bin/python /code/listenbrainz/manage.py spark request_model
    /usr/local/bin/python /code/listenbrainz/manage.py spark request_candidate_sets
    /usr/local/bin/python /code/listenbrainz/manage.py spark request_recommendations --top=1000 --similar=1000
}

RECOMMENDATION_TYPE="$1"

if [ $RECOMMENDATION_TYPE == 'cf' ]; then
    invoke_cf_recommendation_scripts
else
    echo 'Unknown recommendation type!'
fi
