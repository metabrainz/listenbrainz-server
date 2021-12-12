from listenbrainz_spark.stats.user.entity import get_entity_stats


def calculate_top_entity_stats():
    yield get_entity_stats("artists", "this_year", "year_in_music_top_stats")
    yield get_entity_stats("recordings", "this_year", "year_in_music_top_stats")
    yield get_entity_stats("releases", "this_year", "year_in_music_top_stats")
