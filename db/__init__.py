from flask_sqlalchemy import SQLAlchemy

# This value must be incremented after schema changes on replicated tables!
SCHEMA_VERSION = 1

# Be careful when importing `_connection` before init_connection function is
# called! In general helper functions like `create_cursor` or `commit` should
# be used. Feel free to add new ones if some functionality is missing.
db = SQLAlchemy()


def init_db_connection(app):
    """Initializes database connection using the specified Flask app.

    Configuration file must contain `SQLALCHEMY_DATABASE_URI` key. See
    https://pythonhosted.org/Flask-SQLAlchemy/config.html#configuration-keys
    for more info.
    """
    global db
    db.init_app(app)


def run_sql_script(sql_file_path):
    with open(sql_file_path) as sql:
        db.session.connection().execute(sql.read())
