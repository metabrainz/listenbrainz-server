from listenbrainz_spark.stats.user.entity import get_entity_stats, calculate_entity_stats
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year


def calculate_top_entity_stats(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    table = "listens_of_year"
    listens = get_listens_from_new_dump(from_date, to_date)
    listens.createOrReplaceTempView(table)

    for entity in ["artists", "recordings", "releases"]:
        stats = calculate_entity_stats(
            start, end, table, entity, "this_year", "year_in_music_top_stats"
        )
        for message in stats:
            yield message
