from listenbrainz_spark.postgres.artist import create_artist_country_cache
from listenbrainz_spark.postgres.artist_credit import create_artist_credit_cache
from listenbrainz_spark.postgres.recording import create_recording_length_cache
from listenbrainz_spark.postgres.release import create_release_metadata_cache


def import_all_pg_tables():
    """ Import all tables from the postgres database. """
    create_artist_country_cache()
    create_artist_credit_cache()
    create_recording_length_cache()
    create_release_metadata_cache()
