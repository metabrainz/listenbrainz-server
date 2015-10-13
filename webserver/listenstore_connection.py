from listenstore import listenstore
from flask import current_app

def get_listenstore():
    server = current_app.config['CASSANDRA_SERVER']
    keyspace = current_app.config['CASSANDRA_KEYSPACE']
    return listenstore.ListenStore({
        'cassandra_server': server,
        'cassandra_keyspace': keyspace,
    })
