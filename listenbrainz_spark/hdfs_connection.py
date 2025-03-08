import logging
import os
import sys

import hdfs

logger = logging.getLogger(__name__)

logger.info("sys path: %s", sys.path)
logger.info("environment: %s", os.environ)
logger.info("hdfs contents: %s", dir(hdfs))
client = None


def init_hdfs(namenode_uri, user=None):
    if user is None:
        user = os.environ["USER"]
    global client
    client = hdfs.InsecureClient(namenode_uri, user=user)
