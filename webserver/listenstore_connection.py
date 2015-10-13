import listenstore

def init_listenstore(server, keyspace):
    return listenstore.ListenStore({
        'cassandra_server': server,
        'cassandra_keyspace': keyspace,
    })
