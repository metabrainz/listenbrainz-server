import listenbrainz_spark.recommendations.candidate_sets
import listenbrainz_spark.recommendations.create_dataframes
import listenbrainz_spark.recommendations.recommend
import listenbrainz_spark.recommendations.train_models
import listenbrainz_spark.request_consumer.jobs.import_dump
import listenbrainz_spark.stats.sitewide.entity
import listenbrainz_spark.stats.user.daily_activity
import listenbrainz_spark.stats.user.entity
import listenbrainz_spark.stats.user.listening_activity

functions = {
    'stats.user.entity.week': listenbrainz_spark.stats.user.entity.get_entity_week,
    'stats.user.entity.month': listenbrainz_spark.stats.user.entity.get_entity_month,
    'stats.user.entity.year': listenbrainz_spark.stats.user.entity.get_entity_year,
    'stats.user.entity.all_time': listenbrainz_spark.stats.user.entity.get_entity_all_time,
    'stats.user.listening_activity.week': listenbrainz_spark.stats.user.listening_activity.get_listening_activity_week,
    'stats.user.listening_activity.month': listenbrainz_spark.stats.user.listening_activity.get_listening_activity_month,
    'stats.user.listening_activity.year': listenbrainz_spark.stats.user.listening_activity.get_listening_activity_year,
    'stats.user.listening_activity.all_time': listenbrainz_spark.stats.user.listening_activity.get_listening_activity_all_time,
    'stats.user.daily_activity.week': listenbrainz_spark.stats.user.daily_activity.get_daily_activity_week,
    'stats.user.daily_activity.month': listenbrainz_spark.stats.user.daily_activity.get_daily_activity_month,
    'stats.user.daily_activity.year': listenbrainz_spark.stats.user.daily_activity.get_daily_activity_year,
    'stats.user.daily_activity.all_time': listenbrainz_spark.stats.user.daily_activity.get_daily_activity_all_time,
    'stats.sitewide.entity.week': listenbrainz_spark.stats.sitewide.entity.get_entity_week,
    'stats.sitewide.entity.month': listenbrainz_spark.stats.sitewide.entity.get_entity_month,
    'stats.sitewide.entity.year': listenbrainz_spark.stats.sitewide.entity.get_entity_year,
    'stats.sitewide.entity.all_time': listenbrainz_spark.stats.sitewide.entity.get_entity_all_time,
    'import.dump.full_newest': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_full_dump_handler,
    'import.dump.full_id': listenbrainz_spark.request_consumer.jobs.import_dump.import_full_dump_by_id_handler,
    'import.dump.incremental_newest': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_incremental_dump_handler,
    'import.dump.incremental_id': listenbrainz_spark.request_consumer.jobs.import_dump.import_incremental_dump_by_id_handler,
    'cf_recording.recommendations.create_dataframes': listenbrainz_spark.recommendations.create_dataframes.main,
    'cf_recording.recommendations.train_model': listenbrainz_spark.recommendations.train_models.main,
    'cf_recording.recommendations.candidate_sets': listenbrainz_spark.recommendations.candidate_sets.main,
    'cf_recording.recommendations.recommend': listenbrainz_spark.recommendations.recommend.main,
    'import.mapping': listenbrainz_spark.request_consumer.jobs.import_dump.import_mapping_to_hdfs,
    'import.artist_relation': listenbrainz_spark.request_consumer.jobs.import_dump.import_artist_relation_to_hdfs,
}


def get_query_handler(query):
    return functions[query]
