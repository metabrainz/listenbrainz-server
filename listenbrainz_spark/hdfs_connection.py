import os

import hdfs

client = None


def init_hdfs(namenode_uri, user=None):
    if user is None:
        user = os.environ["USER"]
    global client
    client = hdfs.InsecureClient(namenode_uri, user=user)
