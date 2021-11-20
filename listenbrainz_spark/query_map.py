import listenbrainz_spark.recommendations.recording.candidate_sets
import listenbrainz_spark.recommendations.recording.create_dataframes
import listenbrainz_spark.recommendations.recording.recommend
import listenbrainz_spark.recommendations.recording.train_models
import listenbrainz_spark.user_similarity.user_similarity
import listenbrainz_spark.request_consumer.jobs.import_dump
import listenbrainz_spark.stats.sitewide.entity
import listenbrainz_spark.stats.user.daily_activity
import listenbrainz_spark.stats.user.entity
import listenbrainz_spark.stats.user.listening_activity
import listenbrainz_spark.year_in_music.new_releases_of_top_artists
import listenbrainz_spark.year_in_music.most_prominent_color
import listenbrainz_spark.year_in_music.similar_users

functions = {
    'stats.user.entity': listenbrainz_spark.stats.user.entity.get_entity_stats,
    'stats.user.listening_activity': listenbrainz_spark.stats.user.listening_activity.get_listening_activity,
    'stats.user.daily_activity': listenbrainz_spark.stats.user.daily_activity.get_daily_activity,
    'stats.sitewide.entity': listenbrainz_spark.stats.sitewide.entity.get_entity_stats,
    'stats.new_releases_of_top_artists': listenbrainz_spark.year_in_music.new_releases_of_top_artists.get_new_releases_of_top_artists,
    'stats.most_prominent_color': listenbrainz_spark.year_in_music.most_prominent_color.get_most_prominent_color,
    'import.dump.full_newest': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_full_dump_handler,
    'import.dump.full_id': listenbrainz_spark.request_consumer.jobs.import_dump.import_full_dump_by_id_handler,
    'import.dump.incremental_newest': listenbrainz_spark.request_consumer.jobs.import_dump.import_newest_incremental_dump_handler,
    'import.dump.incremental_id': listenbrainz_spark.request_consumer.jobs.import_dump.import_incremental_dump_by_id_handler,
    'cf.recommendations.recording.create_dataframes': listenbrainz_spark.recommendations.recording.create_dataframes.main,
    'cf.recommendations.recording.train_model': listenbrainz_spark.recommendations.recording.train_models.main,
    'cf.recommendations.recording.candidate_sets': listenbrainz_spark.recommendations.recording.candidate_sets.main,
    'cf.recommendations.recording.recommendations': listenbrainz_spark.recommendations.recording.recommend.main,
    'import.artist_relation': listenbrainz_spark.request_consumer.jobs.import_dump.import_artist_relation_to_hdfs,
    'import.musicbrainz_release_dump': listenbrainz_spark.request_consumer.jobs.import_dump.import_release_json_dump_to_hdfs,
    'similarity.similar_users': listenbrainz_spark.user_similarity.user_similarity.main,
    'similarity.similar_users_2021': listenbrainz_spark.year_in_music.similar_users.get_similar_users,
}


def get_query_handler(query):
    return functions[query]
