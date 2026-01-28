import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Union

from pyspark import Row
from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark import config, hdfs_connection
from listenbrainz_spark.hdfs.utils import create_dir
from listenbrainz_spark.path import LISTENBRAINZ_LISTENS_METADATA, LISTENBRAINZ_LISTENS_DIRECTORY_PREFIX
from listenbrainz_spark.schema import listens_metadata_schema

_listens_metadata_df: Optional[DataFrame] = None


def get_listens_metadata() -> Union[Row, None]:
    """ Retrieve listens metadata from HDFS """
    global _listens_metadata_df
    if _listens_metadata_df is None \
        and hdfs_connection.client.status(LISTENBRAINZ_LISTENS_METADATA, strict=False):
        _listens_metadata_df = listenbrainz_spark \
            .session \
            .read \
            .json(config.HDFS_CLUSTER_URI + LISTENBRAINZ_LISTENS_METADATA, schema=listens_metadata_schema)

    if _listens_metadata_df is not None:
        return _listens_metadata_df.collect()[0]


def update_listens_metadata(new_location, max_listened_at, max_created):
    """ Update listens metadata in HDFS """
    row = Row(
        location=new_location,
        max_listened_at=max_listened_at,
        max_created=max_created,
        updated_at=datetime.now(timezone.utc)
    )
    listenbrainz_spark \
        .session \
        .createDataFrame([row], schema=listens_metadata_schema) \
        .repartition(1) \
        .write \
        .mode("overwrite") \
        .json(config.HDFS_CLUSTER_URI + LISTENBRAINZ_LISTENS_METADATA)

    unpersist_listens_metadata()


def unpersist_listens_metadata():
    global _listens_metadata_df
    if _listens_metadata_df is not None:
        _listens_metadata_df.unpersist()
        _listens_metadata_df = None


def generate_new_listens_location() -> str:
    location = os.path.join(LISTENBRAINZ_LISTENS_DIRECTORY_PREFIX, str(uuid.uuid4()))
    create_dir(location)
    return location
