CREATE TYPE cf_recording_type AS ENUM('top_artist', 'similar_artist');

CREATE TYPE mb_missing_data_source_enum AS ENUM('cf', 'artist_map');

CREATE TYPE user_relationship_enum AS ENUM('follow');

CREATE TYPE recommendation_feedback_type_enum AS ENUM('like', 'love', 'dislike', 'hate', 'bad_recommendation');

CREATE TYPE user_timeline_event_type_enum AS ENUM('recording_recommendation', 'notification', 'critiquebrainz_review', 'personal_recording_recommendation', 'thanks');

CREATE TYPE hide_user_timeline_event_type_enum AS ENUM('recording_recommendation', 'personal_recording_recommendation', 'recording_pin');

CREATE TYPE external_service_oauth_type AS ENUM ('spotify', 'youtube', 'critiquebrainz', 'lastfm', 'librefm', 'musicbrainz', 'soundcloud', 'apple', 'musicbrainz-prod', 'musicbrainz-beta', 'musicbrainz-test');

CREATE TYPE stats_range_type AS ENUM ('week', 'month', 'quarter', 'half_yearly', 'year', 'all_time',
    'this_week', 'this_month', 'this_year');

CREATE TYPE user_stats_type AS ENUM('artists', 'releases', 'recordings', 'daily_activity', 'listening_activity', 'artist_map');

CREATE TYPE do_not_recommend_entity_type AS ENUM ('artist', 'release', 'release_group', 'recording');

CREATE TYPE background_tasks_type AS ENUM ('delete_listens', 'delete_user', 'export_all_user_data');

CREATE TYPE user_data_export_status_type AS ENUM ('in_progress', 'waiting', 'completed', 'failed');

CREATE TYPE user_data_export_type_type AS ENUM ('export_all_user_data');

CREATE TYPE data_dump_type_type AS ENUM ('incremental', 'full');
