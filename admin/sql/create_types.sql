CREATE TYPE cf_recording_type AS ENUM('top_artist', 'similar_artist');

CREATE TYPE mb_missing_data_source_enum AS ENUM('cf', 'artist_map');

CREATE TYPE user_relationship_enum AS ENUM('follow');

CREATE TYPE feedback_type_enum AS ENUM('like_rec', 'love_rec', 'dislike_rec', 'hate_rec', 'bad_rec');
