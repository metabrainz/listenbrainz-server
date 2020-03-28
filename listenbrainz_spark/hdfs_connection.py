import hdfs

client = None

def init_hdfs(namenode_uri, user='root'):
    global client
    client = hdfs.InsecureClient(namenode_uri, user='root')
