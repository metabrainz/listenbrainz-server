#!/bin/bash

/usr/local/bin/python /code/listenbrainz/manage.py spark request_dataframes --job-type="similar_users" --days=365 --listens-threshold=50
/usr/local/bin/python /code/listenbrainz/manage.py spark request_similar_users
