""" This script takes all listens in the ListenBrainz influx database and
submits them to Google BigQuery.
"""

# listenbrainz-server - Server for the ListenBrainz project
#
# Copyright (C) 2018 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import json
import listenbrainz.config as config
import listenbrainz.db as db
import listenbrainz.db.user as db_user
import listenbrainz.utils as utils
import os
import time


from datetime import datetime
from googleapiclient.errors import HttpError
from influxdb import InfluxDBClient
from listenbrainz.bigquery import create_bigquery_object
from listenbrainz.bigquery_writer.bigquery_writer import BigQueryWriter
from listenbrainz.listen import Listen

CHUNK_SIZE = 1000

influx = None
bigquery = None


def init_influx_connection():
    """ Initializes the connection to the Influx database.
    """
    global influx
    influx = InfluxDBClient(
        host=config.INFLUX_HOST,
        port=config.INFLUX_PORT,
        database=config.INFLUX_DB_NAME,
    )


def init_bigquery_connection():
    """ Initiates the connection to Google BigQuery.
    """
    global bigquery
    bigquery = create_bigquery_object()


def convert_to_influx_timestamp(year):
    """ Returns the timestamp for the first second of the specified year in
    the format that influx accepts.
    """
    ts = datetime(year, 1, 1, 0, 0, 0).strftime('%s')
    return utils.get_influx_query_timestamp(ts)


def get_listens_batch(user_name, start_year, end_year, offset=0):
    """ Get a batch of listens for the specified user.

    Args:
        user_name (str): the MusicBrainz ID of the user
        start_year (int): the first year in the time range for which listens are to be returned
        end_year (int): the last year in the time range (exclusive)
        offset (int): the offset used to identify which batch of listens to return

    Returns:
        a list of listens in ListenBrainz API format
    """
    condition = 'time >= %s AND time < %s' % (convert_to_influx_timestamp(start_year), convert_to_influx_timestamp(end_year))
    query = """SELECT *
                 FROM {measurement_name}
                WHERE {condition}
             ORDER BY time
                LIMIT {limit}
               OFFSET {offset}
            """.format(
                measurement_name=utils.get_escaped_measurement_name(user_name),
                condition=condition,
                limit=CHUNK_SIZE,
                offset=offset,
            )

    while True:
        try:
            result = influx.query(query)
            break
        except Exception as e:
            print('Error while getting listens from influx: %s' % str(e))
            time.sleep(3)

    listens = []
    for row in result.get_points(utils.get_measurement_name(user_name)):
        listen = Listen.from_influx(row).to_api()
        listen['user_name'] = user_name
        listens.append(listen)

    return listens


def push_to_bigquery(listens, table_name):
    """ Push a list of listens to the specified table in Google BigQuery

    Args:
        listens: the list of listens to be pushed to Google BigQuery
        table_name: the name of the table in which listens are to be inserted

    Returns:
        int: the number of listens pushed to Google BigQuery
    """
    print('Pushing %d listens to table %s' % (len(listens), table_name))
    payload = {
        'rows': BigQueryWriter().convert_to_bigquery_payload(listens)
    }
    while True:
        try:
            ret = bigquery.tabledata().insertAll(
                projectId=config.BIGQUERY_PROJECT_ID,
                datasetId=config.BIGQUERY_DATASET_ID,
                tableId=table_name,
                body=payload).execute(num_retries=5)
            break
        except HttpError as e:
            print('Submit to BigQuery failed: %s, retrying in 3 seconds.' % str(e))
        except Exception as e:
            print('Unknown exception on submit to BigQuery failed: %s. Retrying in 3 seconds.' % str(e))
        time.sleep(3)

    return len(listens)


def push_listens(user_name, table_name, start_year, end_year):
    """ Push all listens in a particular time range to the specified table in Google BigQuery

    Args:
        user_name (str): the MusicBrainz ID of the user
        table_name (str): the name of the table into which listens are to be inserted
        start_year (int): the beginning year of the time range (inclusive)
        end_year (int): the end year of the time range (exclusive)

    Returns:
        int: the number of listens pushed to Google BigQuery
    """
    print('Pushing listens to table %s for user %s' % (table_name, user_name))
    offset = 0
    count = 0
    while True:
        listens = get_listens_batch(
            user_name,
            start_year=start_year,
            end_year=end_year,
            offset=offset,
        )
        if not listens:
            break
        count += push_to_bigquery(listens, table_name)
        offset += CHUNK_SIZE
    return count


def load_fields():
    """ Returns the fields in the ListenBrainz Google BigQuery schema
    """
    schema_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'admin', 'bigquery')
    with open(os.path.join(schema_dir, 'listen-schema.json')) as f:
        return json.load(f)


def create_table(table_name):
    """ Create a table with specified name in Google BigQuery.
    """
    try:
        result = bigquery.tables().get(
            projectId=config.BIGQUERY_PROJECT_ID,
            datasetId=config.BIGQUERY_DATASET_ID,
            tableId=table_name,
        ).execute(num_retries=5)
        if 'creationTime' in result:
            print('Table %s already present and created in BigQuery, returning...' % table_name)
            return
    except HttpError as e:
        if e.resp.status != 404:
            print('Error while getting information for table %s...' % table_name)
            raise

    creation_request_body = {
        'tableReference': {
            'projectId': config.BIGQUERY_PROJECT_ID,
            'datasetId': config.BIGQUERY_DATASET_ID,
            'tableId': table_name,
        },
        'schema': {
            'fields': load_fields()
        },
    }

    response = bigquery.tables().insert(
        projectId=config.BIGQUERY_PROJECT_ID,
        datasetId=config.BIGQUERY_DATASET_ID,
        body=creation_request_body,
    ).execute(num_retries=5)
    print('Table %s created!' % table_name)


def create_all_tables():
    """ Create all Google BigQuery tables.

    Note: This function does nothing if tables are already present in the dataset
    """
    create_table('before_2002') # extra table for listens before Last.FM (should be bad data)
    for year in range(2002, 2019):
        create_table(str(year))


def main():
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    init_influx_connection()
    init_bigquery_connection()
    create_all_tables()
    count = 0
    for user in db_user.get_all_users():
        count += push_listens(user['musicbrainz_id'], 'before_2002', start_year=1970, end_year=2002)
        for year in range(2002, 2019):
            count += push_listens(user['musicbrainz_id'], table_name=str(year), start_year=year, end_year=year+1)
    print('A total of %d listens restreamed to Google BigQuery' % count)


if __name__ == '__main__':
    main()
