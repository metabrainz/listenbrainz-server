import listenbrainz_spark.stats.user.all

functions = {
	'stats.user.all': listenbrainz_spark.stats.user.all.calculate,
}


def get_query_handler(query):
    return functions[query]
