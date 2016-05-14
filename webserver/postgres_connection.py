from listenstore.listenstore import PostgresListenStore

def init_postgres_connection(database_uri):
    return PostgresListenStore({
        'sqlalchemy_database_uri': database_uri,
    })
