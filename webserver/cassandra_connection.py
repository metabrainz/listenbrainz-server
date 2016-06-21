from listenstore.listenstore import CassandraListenStore

def init_cassandra_connection(server, keyspace, rep_factor):
    return CassandraListenStore({
        'CASSANDRA_SERVER': server,
        'CASSANDRA_KEYSPACE': keyspace,
        'CASSANDRA_REPLICATION_FACTOR': rep_factor,
    })
