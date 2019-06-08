from pyspark.sql import Row
from pyspark.sql.types import StructField, StructType, StringType, TimestampType

avro_schema = StructType([
    StructField('listened_at', TimestampType(), nullable=True),
    StructField('user_name', StringType(), nullable=False),
    StructField('artist_mbid', StringType(), nullable=True),
    StructField('release_mbid', StringType(), nullable=True),
    StructField('recording_mbid', StringType(), nullable=True),
])
