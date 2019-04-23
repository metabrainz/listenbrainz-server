from pyspark.sql import Row
from pyspark.sql.types import StructField, StructType, StringType, TimestampType


# NOTE: please keep this schema definition alphabetized
mlhd_schema = [
    StructField('artist_mbid', StringType(), nullable=True),
    StructField('listened_at', TimestampType(), nullable=True),
    StructField('recording_mbid', StringType(), nullable=True),
    StructField('release_mbid', StringType(), nullable=True),
]

# The field names of the schema need to be sorted, otherwise we get weird
# errors due to type mismatches when creating DataFrames using the schema
# Although, we try to keep it sorted in the actual definition itself, we
# also sort it programmatically just in case
mlhd_schema = StructType(sorted(mlhd_schema, key=lambda field: field.name))

tsv_schema = StructType([
    StructField('listened_at', TimestampType(), nullable=True),
    StructField('artist_mbid', StringType(), nullable=True),
    StructField('release_mbid', StringType(), nullable=True),
    StructField('recording_mbid', StringType(), nullable=True),
])
avro_schema = StructType([
    StructField('listened_at', TimestampType(), nullable=True),
    StructField('user_name', StringType(), nullable=False),
    StructField('artist_mbid', StringType(), nullable=True),
    StructField('release_mbid', StringType(), nullable=True),
    StructField('recording_mbid', StringType(), nullable=True),
])
