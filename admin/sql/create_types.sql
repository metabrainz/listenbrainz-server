CREATE TYPE cf_recording_type AS ENUM('top_artist', 'similar_artist');

CREATE TYPE mb_missing_data_source_enum AS ENUM('cf', 'artist_map');

CREATE TYPE user_relationship_enum AS ENUM('follow');

CREATE TYPE recommendation_feedback_type_enum AS ENUM('like', 'love', 'dislike', 'hate', 'bad_recommendation');

CREATE TYPE user_timeline_event_type_enum AS ENUM('recording_recommendation', 'notification');

CREATE TYPE external_service_oauth_type AS ENUM ('spotify', 'youtube');
