import json
import os
import sys
from collections import defaultdict
from pyspark import SparkConf, SparkContext


IMPORT_CHUNK_SIZE = 100000
WRITE_RDDS_TO_DISK = False


def load_listenbrainz_dump(directory, sc):
    """
    Reads files from an uncompressed ListenBrainz dump and creates user and listens RDDs.

    Args:
        directory: Path of the directory containing the LB dump files.
        sc: The SparkContext object.

    Returns:
        users_rdd: RDD containing user info (user_id, user_name).
        listens_rdd: RDD containing ALL listens with user-names.
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
        users.append((i, user))

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
                    listen = (listen["user_name"], listen["listened_at"], listen["recording_msid"], listen["track_metadata"]["track_name"], json.dumps(listen["track_metadata"]))
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
    listens_rdd.persist()
    users_rdd.persist()
    return users_rdd, listens_rdd


def prepare_recording_data(listens_rdd):
    """
    Returns an RDD of the form (recording_id: (recording_msid, track_name))
    """
    recordings_rdd = listens_rdd.map(lambda r: (r[2], r[3])).distinct().zipWithIndex().map(lambda r: (r[1], r[0]))
    return recordings_rdd


def prepare_listen_counts():
    """ calculates ratings, returns rdd of the form (user_id, recording_id, play_count)
    """
    raise NotImplementedError


def get_listen_counts_for_user(user_id):
    """ returns rdd for a user's recording play counts
    (user_id = specified user id, recording_id, play_count)
    """
    raise NotImplementedError


if __name__ == '__main__':
    conf = SparkConf() \
      .setAppName("LB recommender") \
      .set("spark.executor.memory", "1g")
    sc = SparkContext(conf=conf)

    directory = sys.argv[1]
    users_rdd, listens_rdd = load_listenbrainz_dump(directory, sc)
    recordings_rdd = prepare_recording_data(listens_rdd)
