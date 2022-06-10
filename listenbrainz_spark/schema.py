from datetime import datetime
from pyspark.sql import Row
from pyspark.sql.types import StructField, StructType, ArrayType, StringType, TimestampType, FloatType, \
    IntegerType, LongType, DoubleType, DecimalType

listens_new_schema = StructType([
    StructField('listened_at', TimestampType(), nullable=False),
    StructField('user_id', IntegerType(), nullable=False),
    StructField('artist_name', StringType(), nullable=False),
    StructField('artist_credit_id', LongType(), nullable=True),
    StructField('release_name', StringType(), nullable=True),
    StructField('release_mbid', StringType(), nullable=True),
    StructField('recording_name', StringType(), nullable=False),
    StructField('recording_mbid', StringType(), nullable=True),
    StructField('artist_credit_mbids', ArrayType(StringType()), nullable=True),
])

release_radar_schema = StructType([
    StructField('date', StringType(), nullable=False),
    StructField('artist_credit_name', StringType(), nullable=False),
    StructField('artist_mbids', ArrayType(StringType()), nullable=False),
    StructField('release_name', StringType(), nullable=False),
    StructField('release_mbid', StringType(), nullable=False),
    StructField('release_group_primary_type', StringType(), nullable=True),
    StructField('release_group_secondary_type', StringType(), nullable=True)
])

recommendation_schema = StructType([
    StructField('user_id', IntegerType(), nullable=False),
    StructField('recs', ArrayType(StructType([
        StructField('latest_listened_at', StringType(), nullable=True),
        StructField('recording_mbid', StringType(), nullable=True),
        StructField('score', FloatType(), nullable=True)
    ])), nullable=False)
])


# schema to contain model parameters.
model_param_schema = [
    StructField('alpha', FloatType(), nullable=True),  # Baseline level of confidence weighting applied.
    StructField('iteration', IntegerType(), nullable=True),  # Number of iterations to run.
    StructField('lmbda', FloatType(), nullable=True),  # Controls over fitting.
    StructField('rank', IntegerType(), nullable=True),  # Number of hidden features in our low-rank approximation matrices.
]
model_param_schema = StructType(sorted(model_param_schema, key=lambda field: field.name))


model_metadata_schema = [
    StructField('dataframe_id', StringType(), nullable=False),  # dataframe id or identification string of dataframe.
    StructField('model_created', TimestampType(), nullable=False),  # Timestamp when the model is saved in HDFS.
    StructField('model_html_file', StringType(), nullable=False),  # Model html file name
    StructField('model_id', StringType(), nullable=False),  # Model id or identification string of best model.
    StructField('model_param', model_param_schema, nullable=False),  # Parameters used to train the model.
    StructField('test_rmse', FloatType(), nullable=False),  # Root mean squared error for test data.
    StructField('validation_rmse', FloatType(), nullable=False),  # Root mean squared error for validation data.
]


artist_relation_schema = [
    StructField('id_0', IntegerType(), nullable=False), # artist credit
    StructField('name_1', StringType(), nullable=False), # artist name
    StructField('name_0', StringType(), nullable=False),
    StructField('id_1', IntegerType(), nullable=False),
    StructField('score', FloatType(), nullable=False),
]


dataframe_metadata_schema = [
    StructField('dataframe_created', TimestampType(), nullable=False),  # Timestamp when dataframes are created and saved in HDFS.
    StructField('dataframe_id', StringType(), nullable=False),  # dataframe id or identification string of dataframe.
    # Timestamp from when listens have been used to train, validate and test the model.
    StructField('from_date', TimestampType(), nullable=False),
    # Number of listens recorded in a given time frame (between from_date and to_date, both inclusive).
    StructField('listens_count', IntegerType(), nullable=False),
    StructField('playcounts_count', IntegerType(), nullable=False),  # Summation of training data, validation data and test data.
    StructField('recordings_count', IntegerType(), nullable=False),  # Number of distinct recordings heard in a given time frame.
    # Timestamp till when listens have been used to train, validate and test the model.
    StructField('to_date', TimestampType(), nullable=False),
    StructField('users_count', IntegerType(), nullable=False),  # Number of users active in a given time frame.
]

import_metadata_schema = [
    StructField('dump_id', IntegerType(), nullable=False),   # Id of the dump imported
    StructField('dump_type', StringType(), nullable=False),  # The type of dump imported
    StructField('imported_at', TimestampType(), nullable=False)   # Timestamp when dump is imported
]


# The field names of the schema need to be sorted, otherwise we get weird
# errors due to type mismatches when creating DataFrames using the schema
# Although, we try to keep it sorted in the actual definition itself, we
# also sort it programmatically just in case
model_metadata_schema = StructType(sorted(model_metadata_schema, key=lambda field: field.name))
artist_relation_schema = StructType(sorted(artist_relation_schema, key=lambda field: field.name))
dataframe_metadata_schema = StructType(sorted(dataframe_metadata_schema, key=lambda field: field.name))
import_metadata_schema = StructType(sorted(import_metadata_schema, key=lambda field: field.name))


def convert_model_metadata_to_row(meta):
    """ Convert model metadata to row object.

    Args:
        meta (dict): A dictionary containing model metadata.

    Returns:
        pyspark.sql.Row object - A Spark SQL row.
    """
    return Row(
        dataframe_id=meta.get('dataframe_id'),
        model_created=datetime.utcnow(),
        model_html_file=meta.get('model_html_file'),
        model_id=meta.get('model_id'),
        model_param=Row(
            alpha=meta.get('alpha'),
            iteration=meta.get('iteration'),
            lmbda=meta.get('lmbda'),
            rank=meta.get('rank'),
        ),
        test_rmse=meta.get('test_rmse'),
        validation_rmse=meta.get('validation_rmse'),
    )


def convert_dataframe_metadata_to_row(meta):
    """ Convert dataframe metadata to a pyspark.sql.Row object.

        Args:
            meta (dict): a single dictionary representing model metadata.

        Returns:
            pyspark.sql.Row object - a Spark SQL Row based on the defined dataframe metadata schema.
    """
    return Row(
        dataframe_created=datetime.utcnow(),
        dataframe_id=meta.get('dataframe_id'),
        from_date=meta.get('from_date'),
        listens_count=meta.get('listens_count'),
        playcounts_count=meta.get('playcounts_count'),
        recordings_count=meta.get('recordings_count'),
        to_date=meta.get('to_date'),
        users_count=meta.get('users_count'),
    )
