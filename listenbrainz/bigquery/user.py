from listenbrainz import bigquery
from listenbrainz import config

def delete_user(bigquery_connection, musicbrainz_id):
    """ Deletes all listens for user with specified MusicBrainz ID from Google BigQuery.

    Args:
        bigquery: the bigquery connection object
        musicbrainz_id (str): the MusicBrainz ID of the user
    """
    query = """DELETE FROM {dataset}.{table}
                     WHERE user_name = @user_name
            """.format(dataset=config.BIGQUERY_DATASET_ID, table=config.BIGQUERY_TABLE_ID)

    parameters = [{
        'name': 'user_name',
        'type': 'STRING',
        'value': musicbrainz_id,
    }]

    bigquery.run_query(bigquery_connection, query, parameters, dml=True)
