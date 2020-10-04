CREATE TYPE cf_recording_type AS ENUM('top_artist', 'similar_artist');

CREATE TYPE mb_missing_data_source_enum AS ENUM('cf', 'artist_map');

CREATE TYPE user_relationship_enum AS ENUM('follow');

CREATE TYPE recommendation_feedback_type_enum AS ENUM('like', 'love', 'dislike', 'hate', 'bad_recommendation');
