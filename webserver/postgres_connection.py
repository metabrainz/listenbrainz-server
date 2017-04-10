from listenstore import PostgresListenStore

_postgres = None

def init_postgres_connection(database_uri):
    global _postgres
    _postgres = PostgresListenStore({
        'SQLALCHEMY_DATABASE_URI': database_uri,
    })
    return _postgres
