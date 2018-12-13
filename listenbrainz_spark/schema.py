from datetime import datetime
from pyspark.sql import Row
from pyspark.sql.types import StructField, StructType, ArrayType, StringType, TimestampType


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

# The field names of the schema need to be sorted, otherwise we get weird
# errors due to type mismatches when creating DataFrames using the schema
# Although, we try to keep it sorted in the actual definition itself, we
# also sort it programmatically just in case
listen_schema = StructType(sorted(listen_schema, key=lambda field: field.name))


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
