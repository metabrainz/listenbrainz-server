from datetime import datetime, date, time

from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats.user.entity import calculate_entity_stats, get_entity_stats, entity_cache_map
from listenbrainz_spark.utils import get_listens_from_dump, read_files_from_HDFS


def calculate_top_entity_stats(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    table = "listens_of_year"

    listens = get_listens_from_dump(from_date, to_date)
    listens.createOrReplaceTempView(table)

    df_name = "entity_data_cache"
    for entity in ["artists", "recordings", "releases"]:
        cache_table_path = entity_cache_map.get(entity)
        read_files_from_HDFS(cache_table_path).createOrReplaceTempView(df_name)
        stats = calculate_entity_stats(
            from_date, to_date, table, df_name, entity, "this_year", "year_in_music_top_stats"
        )
        for message in stats:
            # yim stats are stored in postgres instead of couchdb so drop those messages for yim
            if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
                continue

            message["year"] = year
            yield message
