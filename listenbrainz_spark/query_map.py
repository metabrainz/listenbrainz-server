import listenbrainz_spark.stats.user.all
import listenbrainz_spark.stats.user.artist
import listenbrainz_spark.request_consumer.jobs.import_dump
import listenbrainz_spark.recommendations.create_dataframes
import listenbrainz_spark.recommendations.train_models
import listenbrainz_spark.recommendations.candidate_Sets
import listenbrainz_saprk.recommendations.recommend

functions = {
    'stats.user.all': listenbrainz_spark.stats.user.all.calculate,
    'stats.user.artist.week': listenbrainz_spark.stats.user.artist.get_artists_week,
    'stats.user.artist.month': listenbrainz_spark.stats.user.artist.get_artists_month,
    'stats.user.artist.year': listenbrainz_spark.stats.user.artist.get_artists_year,
    'stats.user.artist.all_time': listenbrainz_spark.stats.user.artist.get_artists_all_time,
    'import.dump.full': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_full_dump_handler,
    'recommendations.create_dataframes': listenbrainz_spark.recommendations.create_dataframes.main,
    'recommendations.train_model': listenbrainz_spark.recommendations.train_models.main,
    'recommendations.candidate_sets': listenbrainz_spark.recommendations.candidate_sets.main,
    'recommendations.recommend': listenbrainz_spark.recommendations.recommend.main,
}


def get_query_handler(query):
    return functions[query]
