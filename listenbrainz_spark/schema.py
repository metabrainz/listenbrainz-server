from datetime import datetime
from pyspark.sql import Row
from pyspark.sql.types import StructField, StructType, ArrayType, StringType, TimestampType, FloatType, IntegerType, BooleanType


# NOTE: please keep this schema definition alphabetized
listen_schema = [
    StructField('artist_mbids', ArrayType(StringType()), nullable=True),
    StructField('artist_msid', StringType(), nullable=False),
    StructField('artist_name', StringType(), nullable=False),
    StructField('listened_at', TimestampType(), nullable=False),
    StructField('recording_mbid', StringType(), nullable=True),
    StructField('recording_msid', StringType(), nullable=False),
    StructField('release_mbid', StringType(), nullable=True),
    StructField('release_msid', StringType(), nullable=True),
    StructField('release_name', StringType(), nullable=True),
    StructField('tags', ArrayType(StringType()), nullable=True),
    StructField('track_name', StringType(), nullable=False),
    StructField('user_name', StringType(), nullable=False),
]

model_metadata_schema = [
    StructField('alpha', FloatType(), nullable=True), # Baseline level of confidence weighting applied.
    StructField('created', TimestampType(), nullable=True), # Timestamp when the model is saved in HDFS.
    StructField('deleted', TimestampType(), nullable=True), # Timestamp when the model is deleted from HDFS.
    StructField('lambda', FloatType(), nullable=True), # Controls over fitting.
    # Model id or identification string of best model. Connector for model_metadata_schema and dataframe_metadata_schema.
    StructField('model_id', StringType(), nullable=False),
    StructField('num_iterations', IntegerType(), nullable=True), # Number of iterations to run.
    StructField('rank', IntegerType(), nullable=True), # Number of hidden features in our low-rank approximation matrices.
    StructField('test_data_count', IntegerType(), nullable=True), # Number of listens used to test the model.
    StructField('test_rmse', FloatType(), nullable=True), # Root mean squared error for test data.
    StructField('training_data_count', IntegerType(), nullable=True), # Number of listens used to train the model.
    StructField('updated', BooleanType(), nullable=False) # false by default, set to true when all other fields are filled.
    StructField('validation_data_count', IntegerType(), nullable=True), # Number of listens used to validate the model.
    StructField('validation_rmse', FloatType(), nullable=True), # Root mean squared error for validation data.
]

dataframe_metadata_schema = [
    # Timestamp from when listens have been used to train, validate and test the model.
    StructField('from_date', TimestampType(), nullable=False),
    # Number of listens recorded in a given time frame (between from_date and to_date, both inclusive).
    StructField('listens_count', IntegerType(), nullable=False),
    StructField('model_id', StringType(), nullable=False), # Model id or identification string of best model.
    StructField('playcounts_count', IntegerType(), nullable=False), # Summation of training data, validation data and test data.
    StructField('recordings_count', IntegerType(), nullable=False), # Number of distinct recordings heard in a given time frame.
    # Timestamp till when listens have been used to train, validate and test the model.
    StructField('to_date', TimestampType(), nullable=False),
    StructField('users_count', Timestamp(), nullable=False), # Number of users active in a given time frame.
]

# The field names of the schema need to be sorted, otherwise we get weird
# errors due to type mismatches when creating DataFrames using the schema
# Although, we try to keep it sorted in the actual definition itself, we
# also sort it programmatically just in case
listen_schema = StructType(sorted(listen_schema, key=lambda field: field.name))
model_metadata_schema = StructType(sorted(model_metadata_schema, key=lambda field: field.name))
dataframe_metadata_schema = StructType(sorted(dataframe_metadata_schema, key=lambda field: field.name))

def convert_listen_to_row(listen):
    """ Convert a listen to a pyspark.sql.Row object.

    Args: listen (dict): a single dictionary representing a listen

    Returns:
        pyspark.sql.Row object - a Spark SQL Row based on the defined listen schema
    """
    meta = listen['track_metadata']
    return Row(
        listened_at=datetime.fromtimestamp(listen['listened_at']),
        user_name=listen['user_name'],
        artist_msid=meta['additional_info']['artist_msid'],
        artist_name=meta['artist_name'],
        artist_mbids=meta['additional_info'].get('artist_mbids', []),
        release_msid=meta['additional_info'].get('release_msid', ''),
        release_name=meta.get('release_name', ''),
        release_mbid=meta['additional_info'].get('release_mbid', ''),
        track_name=meta['track_name'],
        recording_msid=listen['recording_msid'],
        recording_mbid=meta['additional_info'].get('recording_mbid', ''),
        tags=meta['additional_info'].get('tags', []),
    )

def convert_to_spark_json(listen):
    meta = listen['track_metadata']
    return {
        'listened_at': str(datetime.fromtimestamp(listen['listened_at'])),
        'user_name': listen['user_name'],
        'artist_msid': meta['additional_info']['artist_msid'],
        'artist_name': meta['artist_name'],
        'artist_mbids': meta['additional_info'].get('artist_mbids', []),
        'release_msid': meta['additional_info'].get('release_msid', ''),
        'release_name': meta.get('release_name', ''),
        'release_mbid': meta['additional_info'].get('release_mbid', ''),
        'track_name': meta['track_name'],
        'recording_msid': listen['recording_msid'],
        'recording_mbid': meta['additional_info'].get('recording_mbid', ''),
        'tags': meta['additional_info'].get('tags', []),
    }
