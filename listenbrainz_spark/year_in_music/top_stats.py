from datetime import datetime, date, time

from listenbrainz_spark.stats.user.entity import calculate_entity_stats
from listenbrainz_spark.utils import get_listens_from_new_dump


def calculate_top_entity_stats(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    table = "listens_of_year"
    listens = get_listens_from_new_dump(from_date, to_date)
    listens.createOrReplaceTempView(table)

    for entity in ["artists", "recordings", "releases"]:
        stats = calculate_entity_stats(
            from_date, to_date, table, entity, "this_year", "year_in_music_top_stats"
        )
        for message in stats:
            # yim stats are stored in postgres instead of couchdb so drop those messages for yim
            if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
                continue

            message["year"] = year
            yield message
