from listenstore.listenstore import ListenStore

_cassandra = None

def init_cassandra_connection(server, keyspace):
    global _cassandra

    _cassandra = ListenStore({ 'cassandra_server' : server,
                               'cassandra_keyspace' : keyspace })
