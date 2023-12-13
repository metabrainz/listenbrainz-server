from datetime import datetime, date, time

from listenbrainz_spark.stats.user.entity import get_entity_stats_for_range


def calculate_top_entity_stats(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)

    for entity in ["artists", "recordings", "release_groups"]:
        stats = get_entity_stats_for_range(
            entity,
            "this_year",
            from_date,
            to_date,
            "year_in_music_top_stats"
        )
        for message in stats:
            # yim stats are stored in postgres instead of couchdb so drop those messages for yim
            if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
                continue

            message["year"] = year
            yield message
