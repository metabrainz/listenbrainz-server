CREATE TYPE cf_recording_type AS ENUM('top_artist', 'similar_artist');

CREATE TYPE mb_missing_data_source_enum AS ENUM('cf', 'artist_map');

CREATE TYPE user_relationship_enum AS ENUM('follow');

CREATE TYPE recommendation_feedback_type_enum AS ENUM('like', 'love', 'dislike', 'hate', 'bad_recommendation');

CREATE TYPE user_timeline_event_type_enum AS ENUM('recording_recommendation', 'notification', 'critiquebrainz_review', 'personal_recording_recommendation');

CREATE TYPE hide_user_timeline_event_type_enum AS ENUM('recording_recommendation', 'recording_pin');

CREATE TYPE external_service_oauth_type AS ENUM ('spotify', 'youtube', 'critiquebrainz', 'lastfm', 'librefm');

CREATE TYPE stats_range_type AS ENUM ('week', 'month', 'quarter', 'half_yearly', 'year', 'all_time',
    'this_week', 'this_month', 'this_year');

CREATE TYPE user_stats_type AS ENUM('artists', 'releases', 'recordings', 'daily_activity', 'listening_activity', 'artist_map');

CREATE TYPE do_not_recommend_entity_type AS ENUM ('artist', 'release', 'release_group', 'recording');
