import ujson
import json
import os
import sys
from collections import defaultdict
from pyspark import SparkConf
from pyspark.sql import Row
from setup import spark, sc

IMPORT_CHUNK_SIZE = 100000
WRITE_RDDS_TO_DISK = False


def prepare_user_data(directory):
    """ Returns a dataframe with user data, columns are (user_id, user_name)
    """
    with open(os.path.join(directory, 'index.json')) as f:
        index = json.load(f)
    users = [(i, user) for i, user in enumerate(index)]
    users_rdd = sc.parallelize(users).map(lambda user: Row(
        user_id=user[0],
        user_name=user[1],
    ))
    users_df = spark.createDataFrame(users_rdd)
    return users_df



def load_listenbrainz_dump(directory):
    """
    Reads files from an uncompressed ListenBrainz dump and creates user and listens RDDs.

    Args:
        directory: Path of the directory containing the LB dump files.

    Returns:
        listens_df: DataFrame containing ALL listens with user-names.
    """

    listens_rdd = sc.parallelize([])
    users = list()
    with open(os.path.join(directory, 'index.json')) as f:
        index = json.load(f)
    files = set([info['file_name'] for _, info in index.items()])
    for file_name in files:
        file_path = os.path.join(directory, 'listens', file_name[0], file_name[0:2], '%s.listens' % file_name)
        listens_rdd = listens_rdd.union(sc.textFile(file_path).map(ujson.loads))

    if WRITE_RDDS_TO_DISK:
        listens_rdd.saveAsTextFile(os.path.join('data', 'listens_rdd'))

    listens_rdd = listens_rdd.map(lambda listen: Row(
        listened_at=listen["listened_at"],
        recording_msid=listen["recording_msid"],
        track_name=listen["track_metadata"]["track_name"],
        user_name=listen["user_name"],
    ))
    listens_df = spark.createDataFrame(listens_rdd)
    return listens_df


def prepare_recording_data(listens_df):
    """
    Returns an RDD of the form (recording_id: (recording_msid, track_name))
    """
    recordings_rdd = listens_df.rdd.map(lambda r: (r["recording_msid"], r["track_name"])).distinct().zipWithIndex()
    recordings_rdd = recordings_rdd.map(lambda recording: Row(
        recording_id = recording[1],
        recording_msid = recording[0][0],
        track_name = recording[0][1],
    ))
    recordings_df = spark.createDataFrame(recordings_rdd)
    return recordings_df


def get_all_play_counts(listens_df, users_df, recordings_df):

    listens_df.createOrReplaceTempView('listen')
    users_df.createOrReplaceTempView('user')
    recordings_df.createOrReplaceTempView('recording')
    playcounts_df = spark.sql("""
        SELECT user_id,
               recording_id,
               count(recording_id) as count
          FROM listen
    INNER JOIN user
            ON listen.user_name = user.user_name
    INNER JOIN recording
            ON recording.recording_msid = listen.recording_msid
      GROUP BY user_id, recording_id
      ORDER BY user_id
    """)
    return playcounts_df


if __name__ == '__main__':

    # dump_directory is the directory with uncompressed LB dump files
    # df_directory is the directory where it is planned to store dataframes
    dump_directory = sys.argv[1]
    df_directory = sys.argv[2]

    users_df = prepare_user_data(dump_directory)
    listens_df = load_listenbrainz_dump(dump_directory)
    recordings_df = prepare_recording_data(listens_df)
    playcounts_df = get_all_play_counts(listens_df, users_df, recordings_df)

    # persist all dfs
    users_df.write.format("parquet").save(os.path.join(df_directory, "user.parquet"))
    listens_df.write.format("parquet").save(os.path.join(df_directory, "listen.parquet"))
    recordings_df.write.format("parquet").save(os.path.join(df_directory, "recording.parquet"))
    playcounts_df.write.format("parquet").save(os.path.join(df_directory, "playcount.parquet"))
