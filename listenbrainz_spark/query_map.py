import listenbrainz_spark.stats.user.all
import listenbrainz_spark.stats.user.artist
import listenbrainz_spark.request_consumer.jobs.import_dump

functions = {
    'stats.user.all': listenbrainz_spark.stats.user.all.calculate,
    'stats.user.artist.week': listenbrainz_spark.stats.user.artist.get_artists_week,
    'stats.user.artist.month': listenbrainz_spark.stats.user.artist.get_artists_month,
    'stats.user.artist.last_year': listenbrainz_spark.stats.user.artist.get_artists_last_year,
    'stats.user.artist.all_time': listenbrainz_spark.stats.user.artist.get_artists_all_time,
    'import.dump.full': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_full_dump_handler,
}


def get_query_handler(query):
    return functions[query]
