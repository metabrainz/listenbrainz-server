import json
import os
import sys
from collections import defaultdict
from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession, Row


IMPORT_CHUNK_SIZE = 100000
WRITE_RDDS_TO_DISK = True

spark = SparkSession \
        .builder \
        .appName("LB recommender") \
        .getOrCreate()


def load_listenbrainz_dump(directory, sc):
    """
    Reads files from an uncompressed ListenBrainz dump and creates user and listens RDDs.

    Args:
        directory: Path of the directory containing the LB dump files.
        sc: The SparkContext object.

    Returns:
        users_df: DataFrame containing user info (user_id, user_name).
        listens_df: DataFrame containing ALL listens with user-names.
    """
    listens_rdd = sc.parallelize([])
    users = list()
    with open(os.path.join(directory, 'index.json')) as f:
        index = json.load(f)
    file_contents = defaultdict(list)
    for i, (user, info) in enumerate(index.items()):
        file_contents[info['file_name']].append({
            'user_name': user,
            'offset': info['offset'],
            'size': info['size'],
        })
        users.append((i+1, user))

    users_rdd = sc.parallelize(users)

    for file_name in file_contents:
        file_contents[file_name] = sorted(file_contents[file_name], key=lambda x: x['offset'])
        file_path = os.path.join(directory, 'listens', file_name[0], file_name[0:2], '%s.listens' % file_name)
        with open(file_path, 'r') as f:
            for user in file_contents[file_name]:
                print('Importing user %s...' % user['user_name'])
                assert(f.tell() == user['offset'])
                bytes_read = 0
                listens = []
                while bytes_read < user['size']:
                    line = f.readline()
                    bytes_read += len(line)
                    listen = json.loads(line)
                    listen["user_name"] = user['user_name']
                    listens.append(listen)
                    if len(listens) > IMPORT_CHUNK_SIZE:
                        listens_rdd = listens_rdd.union(sc.parallelize(listens))
                        listens = []
                    if len(listens) > 0:
                        listens_rdd = listens_rdd.union(sc.parallelize(listens))

                print('Import of user %s done!' % user['user_name'])

    if WRITE_RDDS_TO_DISK:
        users_rdd.saveAsTextFile(os.path.join('data', 'users_rdd'))
        listens_rdd.saveAsTextFile(os.path.join('data', 'listens_rdd'))

    listens_rdd = listens_rdd.map(lambda listen: Row(
        listened_at=listen["listened_at"],
        recording_msid=listen["recording_msid"],
        track_name=listen["track_metadata"]["track_name"],
        user_name=listen["user_name"],
    ))

    users_rdd = users_rdd.map(lambda user: Row(
        user_id=user[0],
        user_name=user[1],
    ))

    listens_df = spark.createDataFrame(listens_rdd)
    users_df = spark.createDataFrame(users_rdd)
    return users_df, listens_df


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
    conf = SparkConf() \
      .setAppName("LB recommender") \
      .set("spark.executor.memory", "1g")
    sc = spark.sparkContext

    # dump_directory is the directory with uncompressed LB dump files
    # df_directory is the directory where it is planned to store dataframes
    dump_directory = sys.argv[1]
    df_directory = sys.argv[2]

    users_df, listens_df = load_listenbrainz_dump(dump_directory, sc)
    recordings_df = prepare_recording_data(listens_df)
    playcounts_df = get_all_play_counts(listens_df, users_df, recordings_df)

    # persist all dfs
    users_df.write.option("path", df_directory).saveAsTable('user')
    listens_df.write.option("path", df_directory).saveAsTable('listen')
    recordings_df.write.option("path", df_directory).saveAsTable('recording')
    playcounts_df.write.option("path", df_directory).saveAsTable('playcount')

    # Example code to read persistent tables into DataFrames
    # listens_df_from_file = spark.table('listen')
    # print(listens_df_from_file.count())
