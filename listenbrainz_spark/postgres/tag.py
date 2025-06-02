from data.postgres.tag import get_tag_or_genre_cache_query
from listenbrainz_spark.path import RECORDING_RECORDING_TAG_DATAFRAME, RECORDING_ARTIST_TAG_DATAFRAME, \
    RECORDING_RELEASE_GROUP_TAG_DATAFRAME, RECORDING_RECORDING_GENRE_DATAFRAME, RECORDING_ARTIST_GENRE_DATAFRAME, \
    RECORDING_RELEASE_GROUP_GENRE_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_tag_cache():
    """ Import tag data from musicbrainz from postgres to HDFS for use in artist map stats calculation. """
    for entity, save_path in [
        ("recording", RECORDING_RECORDING_TAG_DATAFRAME),
        ("artist", RECORDING_ARTIST_TAG_DATAFRAME),
        ("release_group", RECORDING_RELEASE_GROUP_TAG_DATAFRAME)
    ]:
        query = get_tag_or_genre_cache_query(entity, only_genres=False, with_filter=False)
        save_pg_table_to_hdfs(query, save_path)


def create_genre_cache():
    """ Import genre data from musicbrainz from postgres to HDFS for use in year in music stats calculation. """
    for entity, save_path in [
        ("recording", RECORDING_RECORDING_GENRE_DATAFRAME),
        ("artist", RECORDING_ARTIST_GENRE_DATAFRAME),
        ("release_group", RECORDING_RELEASE_GROUP_GENRE_DATAFRAME)
    ]:
        query = get_tag_or_genre_cache_query(entity, only_genres=True, with_filter=False)
        save_pg_table_to_hdfs(query, save_path)
