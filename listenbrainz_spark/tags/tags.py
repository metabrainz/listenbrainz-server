from more_itertools import chunked

from listenbrainz_spark.path import RECORDING_RECORDING_TAG_DATAFRAME, MLHD_RECORDING_POPULARITY_DATAFRAME, \
    RECORDING_ARTIST_TAG_DATAFRAME, RECORDING_RELEASE_GROUP_TAG_DATAFRAME
from listenbrainz_spark.stats import run_query

RECORDINGS_PER_MESSAGE = 1000


def create_messages(recordings_table, popularity_table, source):
    """ For the given type of tags, create the tag dataset with tag_count for each tag, and a percentile rank when ordered
    the recordings by the total_listen_count from
    """
    query = f"""
        WITH intermediate AS (
            SELECT tag
                 , recording_mbid
                 , tag_count
                 , percent_rank() OVER (PARTITION BY tag ORDER BY COALESCE(total_listen_count, 0) DESC) AS _percent
              FROM parquet.`{recordings_table}`
         LEFT JOIN parquet.`{popularity_table}`
             USING (recording_mbid)
        )   SELECT recording_mbid
                 , collect_list(struct(tag, tag_count, _percent)) AS tags
              FROM intermediate
          GROUP BY recording_mbid
    """
    results = run_query(query).toLocalIterator()

    for result in chunked(results, RECORDINGS_PER_MESSAGE):
        data = [tag.asDict(recursive=True) for tag in result]
        yield {
            "type": "tags_dataset",
            "data": data,
            "source": source
        }


def main():
    """ Generate the tags dataset using recording, artist and release group tags """
    yield from create_messages(RECORDING_RECORDING_TAG_DATAFRAME, MLHD_RECORDING_POPULARITY_DATAFRAME, "recording")
    yield from create_messages(RECORDING_ARTIST_TAG_DATAFRAME, MLHD_RECORDING_POPULARITY_DATAFRAME, "artist")
    yield from create_messages(RECORDING_RELEASE_GROUP_TAG_DATAFRAME, MLHD_RECORDING_POPULARITY_DATAFRAME, "release-group")
