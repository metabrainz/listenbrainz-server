import json
import re
from typing import BinaryIO

import requests
import orjson
from requests.adapters import HTTPAdapter
from sentry_sdk import start_span

from urllib3 import Retry

# stat type followed by a underscore followed by a date in YYYYMMDD format
DATABASE_NAME_PATTERN = re.compile(r"([a-zA-Z]+)_(\w+)_(\d{8})")

DATABASE_LOCK_FILE = "LOCK"

_user = None
_admin_key = None
_host = None
_port = None


def init(user, password, host, port):
    """
    Initialize config to connect to couchdb instance.
    
    Args:
        user: couchdb admin user name
        password: couchdb admin password
        host: couchdb service host
        port: couchdb service port
    """
    global _user, _admin_key, _host, _port
    _user = user
    _admin_key = password
    _host = host
    _port = port


def get_base_url():
    return f"http://{_user}:{_admin_key}@{_host}:{_port}"


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

    Before deleting, the existence of a LOCK file is checked. If a file named LOCK,
    exists in the database then it is not deleted.

    Args:
         prefix: the string to match database names with

    Returns:
        tuple of name of databases that were deleted and which matched the prefix
        but weren't deleted
    """
    databases = list_databases(prefix)
    # remove the latest database from the list then delete the databases remaining in the list.
    databases.pop(0)

    deleted, retained = [], []

    for database in databases:
        if check_database_lock(database):
            retained.append(database)
        else:
            response = requests.delete(f"{get_base_url()}/{database}")
            response.raise_for_status()
            deleted.append(database)

    return deleted, retained


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
        docs = orjson.dumps({"docs": data})

    with start_span(op="http", description="insert docs in couchdb using api"):
        couchdb_url = f"{get_base_url()}/{database}/_bulk_docs"
        response = requests.post(couchdb_url, data=docs, headers={"Content-Type": "application/json"})
        response.raise_for_status()


def delete_data(database: str, doc_id: int | str):
    """ Delete the given document from couchdb database.

    Once a document is deleted, it will return a 404 if someone tries to fetch it afterwards. However,
    the document will still remain in the database. To actually remove the document from the database,
    look for the purge endpoint in couchdb docs.

    Args:
         database: the database to delete data from
         doc_id: the id of the document to delete
    """
    document_url = f"{get_base_url()}/{database}/{doc_id}"
    response = requests.head(document_url)
    response.raise_for_status()

    rev = json.loads(response.headers.get("ETag"))
    response = requests.delete(document_url, params={"rev": rev})
    response.raise_for_status()


def check_database_lock(database: str):
    """ Checks whether a database is "currently locked" by checking the existence of
     DATABASE_LOCK_FILE. A database is usually locked only during dumps.
    """
    url = f"{get_base_url()}/{database}/{DATABASE_LOCK_FILE}"
    response = requests.get(url)
    return response.status_code == 200


def lock_database(database: str):
    """ 'Lock' the database so that it does not get deleted.

        Note that, this is not a couchdb feature but a way we made up to co-ordinate process in LB.
        The onus is the on other users to check for existence of the LOCK file before deleting a
        database.
    """
    document_url = f"{get_base_url()}/{database}/{DATABASE_LOCK_FILE}"
    # TODO: figure out why PUT works but POST fails with a weird referer header error
    response = requests.put(document_url, json={})
    response.raise_for_status()


def unlock_database(database: str):
    """ 'Unlock' the database so that it can be cleaned up when needed. """
    delete_data(database, DATABASE_LOCK_FILE)


def _assert_status_hook(r, *args, **kwargs):
    r.raise_for_status()


def _get_requests_session():
    """ Configure a requests session for enforcing common retry strategy and status hooks during dumps. """
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.hooks["response"] = [_assert_status_hook]
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    return http


def dump_database(prefix: str, fp: BinaryIO):
    """ Dump the contents of the earliest database of the asked type.

        The earliest database of the type is chosen because its most probably the complete one while
        the same may not be true for latest one.

        Args:
            prefix: the string to match database names with
            fp: the text stream to dump the contents to
    """
    databases = list_databases(prefix)
    if not databases:
        return

    # get the older database for this stat type because it will likely be the complete one
    # the newer one is probably incomplete and that's why the old one has not been cleaned up yet.
    database = databases[-1]
    lock_database(database)

    try:
        with _get_requests_session() as http:
            database_url = f"{get_base_url()}/{database}"
            response = http.get(database_url)
            total_docs = response.json()["doc_count"]

            limit = 50
            for skip in range(0, total_docs, limit):
                response = http.get(f"{database_url}/_all_docs", params={
                    "skip": skip,
                    "limit": limit,
                    "include_docs": True
                })
                rows = orjson.loads(response.content)["rows"]
                for row in rows:
                    doc = row["doc"]
                    doc.pop("_id", None)
                    doc.pop("key", None)
                    doc.pop("_rev", None)
                    doc.pop("_revisions", None)

                    if not doc:
                        continue

                    fp.write(orjson.dumps(doc, option=orjson.OPT_APPEND_NEWLINE))
    finally:
        unlock_database(database)
