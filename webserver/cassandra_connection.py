from listenstore.listenstore import CassandraListenStore

def init_cassandra_connection(server, keyspace, rep_factor):
    return CassandraListenStore({
        'cassandra_server': server,
        'cassandra_keyspace': keyspace,
        'cassandra_replication_factor': rep_factor,
    })
