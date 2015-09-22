from sqlalchemy import create_engine

# This value must be incremented after schema changes on replicated tables!
SCHEMA_VERSION = 1

engine = None

def init_db_connection(connect_str):
    global engine
    engine = create_engine(connect_str)

def run_sql_script(sql_file_path):
    with open(sql_file_path) as sql:
        connection = engine.connect()
        connection.execute(sql.read())
        connection.close()

