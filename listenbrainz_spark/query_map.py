import listenbrainz_spark.stats.user.all
import listenbrainz_spark.stats.user.entity
import listenbrainz_spark.request_consumer.jobs.import_dump

functions = {
    'stats.user.all': listenbrainz_spark.stats.user.all.calculate,
    'stats.user.entity.week': listenbrainz_spark.stats.user.entity.get_entity_week,
    'stats.user.entity.month': listenbrainz_spark.stats.user.entity.get_entity_month,
    'stats.user.entity.year': listenbrainz_spark.stats.user.entity.get_entity_year,
    'stats.user.entity.all_time': listenbrainz_spark.stats.user.entity.get_entity_all_time,
    'import.dump.full': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_full_dump_handler,
}


def get_query_handler(query):
    return functions[query]
