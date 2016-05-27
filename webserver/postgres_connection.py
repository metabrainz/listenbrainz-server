from listenstore.listenstore import PostgresListenStore

def init_postgres_connection(database_uri):
    return PostgresListenStore({
        'SQLALCHEMY_DATABASE_URI': database_uri,
    })
