from listenbrainz_spark.path import RECORDING_RECORDING_TAG_DATAFRAME, RECORDING_ARTIST_TAG_DATAFRAME, \
    RECORDING_RELEASE_GROUP_TAG_DATAFRAME, RECORDING_RECORDING_GENRE_DATAFRAME, RECORDING_ARTIST_GENRE_DATAFRAME, \
    RECORDING_RELEASE_GROUP_GENRE_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_tag_cache():
    """ Import tag data from musicbrainz from postgres to HDFS for use in artist map stats calculation. """
    _create_cache_base(False, {
        "recording": RECORDING_RECORDING_TAG_DATAFRAME,
        "artist": RECORDING_ARTIST_TAG_DATAFRAME,
        "release_group": RECORDING_RELEASE_GROUP_TAG_DATAFRAME
    })


def create_genre_cache():
    """ Import genre data from musicbrainz from postgres to HDFS for use in year in music stats calculation. """
    _create_cache_base(True, {
        "recording": RECORDING_RECORDING_GENRE_DATAFRAME,
        "artist": RECORDING_ARTIST_GENRE_DATAFRAME,
        "release_group": RECORDING_RELEASE_GROUP_GENRE_DATAFRAME
    })


def _create_cache_base(only_genres, save_paths):
    """ utility function to create tag/genre dataframes """
    if only_genres:
        genre_join = """
            JOIN musicbrainz.genre g
              ON t.name = g.name
        """
        name_alias = "genre"
    else:
        genre_join = ""
        name_alias = "tag"

    query = f"""
        SELECT r.gid AS recording_mbid
             , t.name AS {name_alias}
             , count AS {name_alias}_count
          FROM musicbrainz.tag t
            {genre_join}
          JOIN musicbrainz.recording_tag rt
            ON rt.tag = t.id
          JOIN musicbrainz.recording r
            ON rt.recording = r.id
         WHERE count > 0
    """
    save_pg_table_to_hdfs(query, save_paths["recording"])

    query = f"""
        SELECT r.gid AS recording_mbid
             , t.name AS {name_alias}
             , SUM(count) AS {name_alias}_count
          FROM musicbrainz.recording r
          JOIN musicbrainz.artist_credit_name acn
         USING (artist_credit)
          JOIN musicbrainz.artist a
            ON acn.artist = a.id
          JOIN musicbrainz.artist_tag at
            ON at.artist = a.id
          JOIN musicbrainz.tag t
            ON at.tag = t.id
            {genre_join}
         WHERE count > 0
      GROUP BY r.gid
             , t.name
    """
    save_pg_table_to_hdfs(query, save_paths["artist"])

    query = f"""
    WITH intermediate AS (
        SELECT r.gid AS recording_mbid
             , t.name AS {name_alias}
             , SUM(count) AS {name_alias}_count
          FROM musicbrainz.release_group_tag rgt
          JOIN musicbrainz.tag t
            ON rgt.tag = t.id
            {genre_join}
          JOIN musicbrainz.release_group rg
            ON rgt.release_group = rg.id
          JOIN musicbrainz.release rel
            ON rel.release_group = rg.id
          JOIN musicbrainz.medium m
            ON m.release = rel.id
          JOIN musicbrainz.track tr
            ON tr.medium = m.id
          JOIN musicbrainz.recording r
            ON tr.recording = r.id
         WHERE count > 0
      GROUP BY r.gid
             , t.name
         UNION ALL
        SELECT r.gid AS recording_mbid
             , t.name AS {name_alias}
             , SUM(count) AS {name_alias}_count
          FROM musicbrainz.release_tag rlt
          JOIN musicbrainz.tag t
            ON rlt.tag = t.id
            {genre_join}
          JOIN musicbrainz.release rl
            ON rlt.release = rl.id  
          JOIN musicbrainz.release_group rg
            ON rl.release_group = rg.id
          JOIN musicbrainz.release rel
            ON rel.release_group = rg.id
          JOIN musicbrainz.medium m
            ON m.release = rel.id
          JOIN musicbrainz.track tr
            ON tr.medium = m.id
          JOIN musicbrainz.recording r
            ON tr.recording = r.id
         WHERE count > 0
      GROUP BY r.gid
             , t.name
    ) SELECT recording_mbid
           , {name_alias}
           , CAST(SUM({name_alias}_count) AS BIGINT) AS {name_alias}_count
        FROM intermediate
    GROUP BY recording_mbid
           , {name_alias}
    """
    save_pg_table_to_hdfs(query, save_paths["release_group"])
