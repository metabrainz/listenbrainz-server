from listenbrainz_spark.postgres.artist import create_artist_country_cache
from listenbrainz_spark.postgres.release import create_release_metadata_cache


def import_all_pg_tables():
    create_artist_country_cache()
    create_release_metadata_cache()
