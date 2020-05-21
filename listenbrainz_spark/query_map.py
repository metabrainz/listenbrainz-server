import listenbrainz_spark.stats.user.all
import listenbrainz_spark.stats.user.artist
import listenbrainz_spark.stats.user.release
import listenbrainz_spark.request_consumer.jobs.import_dump

functions = {
    'stats.user.all': listenbrainz_spark.stats.user.all.calculate,
    'stats.user.artist.week': listenbrainz_spark.stats.user.artist.get_artists_week,
    'stats.user.artist.month': listenbrainz_spark.stats.user.artist.get_artists_month,
    'stats.user.artist.year': listenbrainz_spark.stats.user.artist.get_artists_year,
    'stats.user.artist.all_time': listenbrainz_spark.stats.user.artist.get_artists_all_time,
    'stats.user.release.week': listenbrainz_spark.stats.user.release.get_releases_week,
    'stats.user.release.month': listenbrainz_spark.stats.user.release.get_releases_month,
    'stats.user.release.year': listenbrainz_spark.stats.user.release.get_releases_year,
    'stats.user.release.all_time': listenbrainz_spark.stats.user.release.get_releases_all_time,
    'import.dump.full': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_full_dump_handler,
}


def get_query_handler(query):
    return functions[query]
