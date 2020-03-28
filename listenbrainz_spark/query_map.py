import listenbrainz_spark.stats.user.all
import listenbrainz_spark.request_consumer.jobs.import_dump

functions = {
    'stats.user.all': listenbrainz_spark.stats.user.all.calculate,
    'import.dump.full': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_full_dump_handler,
}


def get_query_handler(query):
    return functions[query]
