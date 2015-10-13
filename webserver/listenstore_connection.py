from listenstore import listenstore
from flask import current_app

def get_listenstore():
    return listenstore.ListenStore({
        'cassandra_server': current_app.config['CASSANDRA_SERVER'],
        'cassandra_keyspace': current_app.config['CASSANDRA_KEYSPACE'],
    })
