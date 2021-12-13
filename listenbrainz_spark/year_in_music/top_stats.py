from listenbrainz_spark.stats.user.entity import get_entity_stats


def calculate_top_entity_stats():
    for entity in ["artists", "recordings", "releases"]:
        stats = get_entity_stats(entity, "this_year", "year_in_music_top_stats")
        for message in stats:
            yield message
