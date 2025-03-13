import listenbrainz_spark.missing_mb_data.missing_mb_data
import listenbrainz_spark.recommendations.recording.create_dataframes
import listenbrainz_spark.recommendations.recording.recommend
import listenbrainz_spark.recommendations.recording.discovery
import listenbrainz_spark.recommendations.recording.train_models
import listenbrainz_spark.stats.sitewide.entity
import listenbrainz_spark.stats.sitewide.listening_activity
import listenbrainz_spark.stats.user.daily_activity
import listenbrainz_spark.stats.user.entity
import listenbrainz_spark.stats.user.listening_activity
import listenbrainz_spark.stats.listener.entity
import listenbrainz_spark.year_in_music.new_releases_of_top_artists
import listenbrainz_spark.year_in_music.similar_users
import listenbrainz_spark.year_in_music.day_of_week
import listenbrainz_spark.year_in_music.most_listened_year
import listenbrainz_spark.year_in_music.top_stats
import listenbrainz_spark.year_in_music.listens_per_day
import listenbrainz_spark.year_in_music.listen_count
import listenbrainz_spark.year_in_music.listening_time
import listenbrainz_spark.year_in_music.new_artists_discovered
import listenbrainz_spark.year_in_music.top_genres
import listenbrainz_spark.year_in_music.top_discoveries
import listenbrainz_spark.year_in_music.top_missed_recordings
import listenbrainz_spark.fresh_releases.fresh_releases
import listenbrainz_spark.similarity.recording
import listenbrainz_spark.similarity.artist
import listenbrainz_spark.similarity.user
import listenbrainz_spark.postgres
import listenbrainz_spark.troi.periodic_jams
import listenbrainz_spark.tags.tags
import listenbrainz_spark.mlhd.download
import listenbrainz_spark.mlhd.similarity
import listenbrainz_spark.popularity.main
import listenbrainz_spark.echo.echo
import listenbrainz_spark.listens.dump
import listenbrainz_spark.listens.delete
import listenbrainz_spark.listens.compact

functions = {
    'echo.echo': listenbrainz_spark.echo.echo.handler,
    'stats.entity.listeners': listenbrainz_spark.stats.listener.entity.get_listener_stats,
    'stats.user.entity': listenbrainz_spark.stats.user.entity.get_entity_stats,
    'stats.user.listening_activity': listenbrainz_spark.stats.user.listening_activity.get_listening_activity,
    'stats.user.daily_activity': listenbrainz_spark.stats.user.daily_activity.get_daily_activity,
    'stats.sitewide.entity': listenbrainz_spark.stats.sitewide.entity.get_entity_stats,
    'stats.sitewide.listening_activity': listenbrainz_spark.stats.sitewide.listening_activity.get_listening_activity,
    'import.dump.full': listenbrainz_spark.listens.dump.import_full_dump_handler,
    'import.dump.mlhd': listenbrainz_spark.mlhd.download.import_mlhd_dump_to_hdfs,
    'import.dump.incremental': listenbrainz_spark.listens.dump.import_incremental_dump_handler,
    'cf.missing_mb_data': listenbrainz_spark.missing_mb_data.missing_mb_data.main,
    'cf.recommendations.recording.create_dataframes':
        listenbrainz_spark.recommendations.recording.create_dataframes.main,
    'cf.recommendations.recording.train_model': listenbrainz_spark.recommendations.recording.train_models.main,
    'cf.recommendations.recording.recommendations': listenbrainz_spark.recommendations.recording.recommend.main,
    'cf.recommendations.recording.discovery':
        listenbrainz_spark.recommendations.recording.discovery.get_recording_discovery,
    'similarity.similar_users': listenbrainz_spark.similarity.user.main,
    'similarity.recording.mlhd': listenbrainz_spark.mlhd.similarity.main,
    'similarity.recording': listenbrainz_spark.similarity.recording.main,
    'similarity.artist': listenbrainz_spark.similarity.artist.main,
    'popularity.popularity': listenbrainz_spark.popularity.main.main,
    'year_in_music.new_releases_of_top_artists':
        listenbrainz_spark.year_in_music.new_releases_of_top_artists.get_new_releases_of_top_artists,
    'year_in_music.most_listened_year': listenbrainz_spark.year_in_music.most_listened_year.get_most_listened_year,
    'year_in_music.day_of_week': listenbrainz_spark.year_in_music.day_of_week.get_day_of_week,
    'year_in_music.similar_users': listenbrainz_spark.year_in_music.similar_users.get_similar_users,
    'year_in_music.top_stats': listenbrainz_spark.year_in_music.top_stats.calculate_top_entity_stats,
    'year_in_music.listens_per_day': listenbrainz_spark.year_in_music.listens_per_day.calculate_listens_per_day,
    'year_in_music.listen_count': listenbrainz_spark.year_in_music.listen_count.get_listen_count,
    'year_in_music.new_artists_discovered_count':
        listenbrainz_spark.year_in_music.new_artists_discovered.get_new_artists_discovered_count,
    'year_in_music.listening_time': listenbrainz_spark.year_in_music.listening_time.get_listening_time,
    'year_in_music.top_genres': listenbrainz_spark.year_in_music.top_genres.get_top_genres,
    'year_in_music.top_missed_recordings':
        listenbrainz_spark.year_in_music.top_missed_recordings.generate_top_missed_recordings,
    'year_in_music.top_discoveries': listenbrainz_spark.year_in_music.top_discoveries.generate_top_discoveries,
    'import.pg_metadata_tables': listenbrainz_spark.postgres.import_all_pg_tables,
    'releases.fresh': listenbrainz_spark.fresh_releases.fresh_releases.main,
    'troi.playlists': listenbrainz_spark.troi.periodic_jams.main,
    'tags.default': listenbrainz_spark.tags.tags.main,
    'import.deleted_listens': listenbrainz_spark.listens.delete.main,
    'import.compact_listens': listenbrainz_spark.listens.compact.main
}


def get_query_handler(query):
    return functions[query]
