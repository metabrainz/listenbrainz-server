import re

import requests
import ujson
from flask import current_app
from sentry_sdk import start_span


# stat type followed by a underscore followed by a date in YYYYMMDD format
DATABASE_NAME_PATTERN = re.compile(r"(.*)_(\d{8})")


def get_base_url():
    return f"http://{current_app.config['COUCHDB_USER']}" \
           f":{current_app.config['COUCHDB_ADMIN_KEY']}" \
           f"@{current_app.config['COUCHDB_HOST']}" \
           f":{current_app.config['COUCHDB_PORT']}"


def create_database(database: str):
    """ Create a couchdb database with the given name.

    For example, if prefix is artists_weekly and the day is 2022-07-10 then the newly
    created couchdb database will be named artists_weekly_20220710.

    Args:
         database: the database's name
    """
    databases_url = f"{get_base_url()}/{database}"
    response = requests.put(databases_url)
    response.raise_for_status()


def list_databases(prefix: str) -> list[str]:
    """ List all couchdb database whose name starts with the given prefix
    sorted in the descending order of creation.

    Consider statistics, we generate those daily and create a new database each time for each
    stat daily. We name databases as `prefix_YYYYMMDD` where prefix describes the stat name and
    YYYYMMDD is the date. After statistics for the day have been inserted, we want to get rid
    of the older database for that stat. This method looks up all the databases whose name starts
    with the given prefix.
    """
    databases_url = f"{get_base_url()}/_all_dbs"
    response = requests.get(databases_url)
    response.raise_for_status()
    all_databases = response.json()

    databases = [database for database in all_databases if database.startswith(prefix)]
    databases.sort(reverse=True)
    return databases


def delete_database(prefix: str):
    """ Delete all but the latest database whose name starts with the given prefix.

    Args:
         prefix: the string to match database names with
    """
    databases = list_databases(prefix)
    # remove the latest database from the list then delete the databases remaining in the list.
    databases.pop(0)

    for database in databases:
        databases_url = f"{get_base_url()}/{database}"
        response = requests.delete(databases_url)
        response.raise_for_status()


def fetch_data(prefix: str, user_id: int):
    """ Retrieve data from couchdb for given stat type and user.

    For each stat type, a database is created daily. We do not have a way to do this atomically so the latest
    database for a type may be incomplete when we query it. So, query all databases for given stat 1 by 1 in
    descending order of their creation until user data is found.

    Args:
         prefix: the string to match database names with
         user_id: the user to retrieve data for
    """
    databases = list_databases(prefix)
    base_url = get_base_url()

    for database in databases:
        document_url = f"{base_url}/{database}/{user_id}"
        response = requests.get(document_url)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        return response.json()

    return None


def insert_data(database: str, data: list[dict]):
    """ Insert the given data into the specified database. """
    with start_span(op="serializing", description="serialize data to json"):
        docs = ujson.dumps({"docs": data})

    with start_span(op="http", description="insert docs in couchdb using api"):
        couchdb_url = f"{get_base_url()}/{database}/_bulk_docs"
        response = requests.post(couchdb_url, data=docs, headers={"Content-Type": "application/json"})
        response.raise_for_status()
