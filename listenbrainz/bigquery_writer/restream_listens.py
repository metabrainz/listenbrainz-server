"""
basic idea is do as much stuff as possible in influx

1. create tables dynamically
2. for each user:
        get listens of each year in influx query
        submit them in batches


need to think about table names

last.fm started in 2002, so don't need tables before that, put everything
earlier than that into a bad_data table


"""
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

total_listens_pushed = 0


influx = None
bigquery = None


def init_influx_connection():
    global influx
    influx = InfluxDBClient(
        host=config.INFLUX_HOST,
        port=config.INFLUX_PORT,
        database=config.INFLUX_DB_NAME,
    )


def init_bigquery_connection():
    """ Initiates the connection to Google BigQuery """
    global bigquery
    bigquery = create_bigquery_object()


def convert_to_influx_timestamp(year):
    ts = datetime(year, 1, 1, 0, 0, 0).strftime('%s')
    return utils.get_influx_query_timestamp(ts)


def get_listens_batch(user_name, start_year, end_year, offset=0):
    print('%s - %d - %d - %d' % (user_name, start_year, end_year, offset))
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
            #TODO: add logs
            time.sleep(3)

    listens = []
    for row in result.get_points(utils.get_measurement_name(user_name)):
        listen = Listen.from_influx(row).to_api()
        listen['user_name'] = user_name
        listens.append(listen)

    return listens


def push_to_bigquery(listens, table_name):
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


def push_listens(user_name, table_name, start_year=None, end_year=None):
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
    schema_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'admin', 'bigquery')
    with open(os.path.join(schema_dir, 'listen-schema.json')) as f:
        return json.load(f)


def create_table(table_name):
    print('Trying to create table %s' % table_name)
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
    create_table('before_2002')
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
