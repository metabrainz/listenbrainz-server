from listenbrainz_spark.path import RECORDING_RECORDING_TAG_DATAFRAME, RECORDING_ARTIST_TAG_DATAFRAME, \
    RECORDING_RELEASE_GROUP_TAG_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_tag_cache():
    """ Import tag data from musicbrainz from postgres to HDFS for use in artist map stats calculation. """
    query = """
        SELECT r.gid AS recording_mbid
             , t.name AS tag
             , count AS tag_count
          FROM musicbrainz.tag t
          JOIN musicbrainz.recording_tag rt
            ON rt.tag = t.id
          JOIN musicbrainz.recording r
            ON rt.recording = r.id
         WHERE count > 0
    """
    save_pg_table_to_hdfs(query, RECORDING_RECORDING_TAG_DATAFRAME)

    query = """
        SELECT r.gid AS recording_mbid
             , t.name AS tag
             , SUM(count) AS tag_count
          FROM musicbrainz.recording r
          JOIN musicbrainz.artist_credit_name acn
         USING (artist_credit)
          JOIN musicbrainz.artist a
            ON acn.artist = a.id
          JOIN musicbrainz.artist_tag at
            ON at.artist = a.id
          JOIN musicbrainz.tag t
            ON at.tag = t.id
         WHERE count > 0
      GROUP BY r.gid
             , t.name
    """
    save_pg_table_to_hdfs(query, RECORDING_ARTIST_TAG_DATAFRAME)

    query = """
    WITH intermediate AS (
        SELECT r.gid AS recording_mbid
             , t.name AS tag
             , SUM(count) AS tag_count
          FROM musicbrainz.release_group_tag rgt
          JOIN musicbrainz.tag t
            ON rgt.tag = t.id
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
             , t.name AS tag
             , SUM(count) AS tag_count
          FROM musicbrainz.release_tag rlt
          JOIN musicbrainz.tag t
            ON rlt.tag = t.id
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
           , tag
           , CAST(SUM(tag_count) AS BIGINT) AS tag_count
        FROM intermediate
    GROUP BY recording_mbid
           , tag
    """
    save_pg_table_to_hdfs(query, RECORDING_RELEASE_GROUP_TAG_DATAFRAME)
