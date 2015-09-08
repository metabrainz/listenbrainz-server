from listenstore.listenstore import ListenStore


def init_cassandra_connection(server, keyspace):
    return ListenStore({
        'cassandra_server': server,
        'cassandra_keyspace': keyspace,
    })
