from datetime import datetime
from pyspark.sql import Row
from pyspark.sql.types import StructField, StructType, ArrayType, StringType, TimestampType, FloatType, \
    IntegerType, BooleanType


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
    StructField('model_param', model_param_schema, nullable=False),  # Parameters used to train the model.
    StructField('model_id', StringType(), nullable=False),  # Model id or identification string of best model.
    StructField('test_data_count', IntegerType(), nullable=False),  # Number of listens used to test the model.
    StructField('test_rmse', FloatType(), nullable=False),  # Root mean squared error for test data.
    StructField('training_data_count', IntegerType(), nullable=False),  # Number of listens used to train the model.
    StructField('validation_data_count', IntegerType(), nullable=False),  # Number of listens used to validate the model.
    StructField('validation_rmse', FloatType(), nullable=False),  # Root mean squared error for validation data.
]


msid_mbid_mapping_schema = [
    StructField('mb_artist_credit_id', IntegerType(), nullable=False),
    StructField('mb_artist_credit_mbids', ArrayType(StringType()), nullable=False),
    StructField('mb_recording_mbid', StringType(), nullable=False),
    StructField('mb_release_mbid', StringType(), nullable=False),
    StructField('mb_artist_credit_name', StringType(), nullable=False),
    StructField('msb_artist_credit_name_matchable', StringType(), nullable=False),
    StructField('msb_artist_msid', StringType(), nullable=False),
    StructField('msb_recording_msid', StringType(), nullable=False),
    StructField('msb_release_msid', StringType(), nullable=False),
    StructField('mb_recording_name', StringType(), nullable=False),
    StructField('msb_recording_name_matchable', StringType(), nullable=False),
    StructField('mb_release_name', StringType(), nullable=False),
    StructField('msb_release_name_matchable', StringType(), nullable=False),
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
listen_schema = StructType(sorted(listen_schema, key=lambda field: field.name))
model_metadata_schema = StructType(sorted(model_metadata_schema, key=lambda field: field.name))
msid_mbid_mapping_schema = StructType(sorted(msid_mbid_mapping_schema, key=lambda field: field.name))
artist_relation_schema = StructType(sorted(artist_relation_schema, key=lambda field: field.name))
dataframe_metadata_schema = StructType(sorted(dataframe_metadata_schema, key=lambda field: field.name))
import_metadata_schema = StructType(sorted(import_metadata_schema, key=lambda field: field.name))


def convert_listen_to_row(listen):
    """ Convert a listen to a pyspark.sql.Row object.

        Args:
            listen (dict): a single dictionary representing a listen

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
        model_id=meta.get('model_id'),
        model_param=Row(
            alpha=meta.get('alpha'),
            iteration=meta.get('iteration'),
            lmbda=meta.get('lmbda'),
            rank=meta.get('rank'),
        ),
        test_data_count=meta.get('test_data_count'),
        test_rmse=meta.get('test_rmse'),
        training_data_count=meta.get('training_data_count'),
        validation_data_count=meta.get('validation_data_count'),
        validation_rmse=meta.get('validation_rmse'),
    )


def convert_to_spark_json(listen):
    meta = listen
    return Row(
        listened_at=meta['listened_at'],
        user_name=meta['user_name'],
        artist_msid=meta['artist_msid'],
        artist_name=meta['artist_name'],
        artist_mbids=meta.get('artist_mbids', []),
        release_msid=meta.get('release_msid', ''),
        release_name=meta.get('release_name', ''),
        release_mbid=meta.get('release_mbid', ''),
        track_name=meta['track_name'],
        recording_msid=meta['recording_msid'],
        recording_mbid=meta.get('recording_mbid', ''),
        tags=meta.get('tags', []),
    )


def convert_mapping_to_row(mapping):
    """ Convert model metadata to row object.

        Args:
            mapping (dict): A dictionary containing mapping metadata.

        Returns:
            pyspark.sql.Row object - A Spark SQL row.
    """
    return Row(
        mb_artist_credit_id=mapping.get('mb_artist_credit_id'),
        mb_artist_credit_mbids=mapping.get('mb_artist_credit_mbids'),
        mb_recording_mbid=mapping.get('mb_recording_mbid'),
        mb_release_mbid=mapping.get('mb_release_mbid'),
        mb_artist_credit_name=mapping.get('mb_artist_credit_name'),
        msb_artist_credit_name_matchable=mapping.get('msb_artist_credit_name_matchable'),
        msb_artist_msid=mapping.get('msb_artist_msid'),
        msb_recording_msid=mapping.get('msb_recording_msid'),
        msb_release_msid=mapping.get('msb_release_msid'),
        mb_recording_name=mapping.get('mb_recording_name'),
        msb_recording_name_matchable=mapping.get('msb_recording_name_matchable'),
        mb_release_name=mapping.get('mb_release_name'),
        msb_release_name_matchable=mapping.get('msb_release_name_matchable'),
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
