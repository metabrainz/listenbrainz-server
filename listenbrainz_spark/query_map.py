import listenbrainz_spark.stats.user.all
import listenbrainz_spark.stats.user.entity
import listenbrainz_spark.request_consumer.jobs.import_dump
import listenbrainz_spark.recommendations.create_dataframes
import listenbrainz_spark.recommendations.train_models
import listenbrainz_spark.recommendations.candidate_sets
import listenbrainz_spark.recommendations.recommend

functions = {
    'stats.user.all': listenbrainz_spark.stats.user.all.calculate,
    'stats.user.entity.week': listenbrainz_spark.stats.user.entity.get_entity_week,
    'stats.user.entity.month': listenbrainz_spark.stats.user.entity.get_entity_month,
    'stats.user.entity.year': listenbrainz_spark.stats.user.entity.get_entity_year,
    'stats.user.entity.all_time': listenbrainz_spark.stats.user.entity.get_entity_all_time,
    'import.dump.full': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_full_dump_handler,
    'cf_recording.recommendations.create_dataframes': listenbrainz_spark.recommendations.create_dataframes.main,
    'cf_recording.recommendations.train_model': listenbrainz_spark.recommendations.train_models.main,
    'cf_recording.recommendations.candidate_sets': listenbrainz_spark.recommendations.candidate_sets.main,
    'cf_recording.recommendations.recommend': listenbrainz_spark.recommendations.recommend.main,
}


def get_query_handler(query):
    return functions[query]
