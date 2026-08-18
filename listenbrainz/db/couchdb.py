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


class CouchDBConnection:
    """ Connection details for one CouchDB instance.

    The module level functions below operate on the default connection configured
    via ``init``. Functions that support reading from another CouchDB instance
    (for instance the one the ClickHouse result reader writes stats to) accept an
    optional ``connection`` argument.
    """

    def __init__(self, user, password, host, port, database_prefix):
        self.user = user
        self.admin_key = password
        self.host = host
        self.port = port
        self.database_prefix = database_prefix or ""

    def get_base_url(self):
        return f"http://{self.user}:{self.admin_key}@{self.host}:{self.port}"

    def add_database_prefix(self, database: str):
        return f"{self.database_prefix}{database}"

    def remove_database_prefix(self, database: str):
        if self.database_prefix and database.startswith(self.database_prefix):
            return database[len(self.database_prefix):]
        return database

    def get_database_url(self, database: str):
        return f"{self.get_base_url()}/{self.add_database_prefix(database)}"


_default_connection: CouchDBConnection | None = None


def init(user, password, host, port, database_prefix):
    """
    Initialize config to connect to couchdb instance.
    
    Args:
        user: couchdb admin user name
        password: couchdb admin password
        host: couchdb service host
        port: couchdb service port
        database_prefix: prefix to apply to all application couchdb database names
    """
    global _default_connection
    _default_connection = CouchDBConnection(user, password, host, port, database_prefix)


def _get_connection(connection: CouchDBConnection | None = None) -> CouchDBConnection:
    return connection or _default_connection


def get_base_url():
    return _get_connection().get_base_url()


def _add_database_prefix(database: str):
    return _get_connection().add_database_prefix(database)


def _remove_database_prefix(database: str):
    return _get_connection().remove_database_prefix(database)


def _get_database_url(database: str):
    return _get_connection().get_database_url(database)


def create_database(database: str):
    """ Create a couchdb database with the given name.

    For example, if prefix is artists_weekly and the day is 2022-07-10 then the newly
    created couchdb database will be named artists_weekly_20220710.

    Args:
         database: the database's name
    """
    databases_url = _get_database_url(database)
    response = requests.put(databases_url)
    response.raise_for_status()


def list_databases(stat_prefix: str, connection: CouchDBConnection | None = None) -> list[str]:
    """ List all couchdb database whose name starts with the given stat prefix
    sorted in the descending order of creation.

    Consider statistics, we generate those daily and create a new database each time for each
    stat daily. We name databases as `stat_prefix_YYYYMMDD` where stat_prefix describes the stat
    name and YYYYMMDD is the date. After statistics for the day have been inserted, we want to get
    rid of the older database for that stat. This method looks up all the databases whose name
    starts with the given stat prefix.

    Args:
        stat_prefix: the string to match database names with
        connection: the couchdb instance to query, defaults to the one configured via ``init``
    """
    connection = _get_connection(connection)
    databases_url = f"{connection.get_base_url()}/_all_dbs"
    response = requests.get(databases_url)
    response.raise_for_status()
    all_databases = response.json()

    database_prefixed_stat_prefix = connection.add_database_prefix(stat_prefix)
    databases = [
        connection.remove_database_prefix(database)
        for database in all_databases
        if database.startswith(database_prefixed_stat_prefix)
    ]
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
            response = requests.delete(_get_database_url(database))
            response.raise_for_status()
            deleted.append(database)

    return deleted, retained


def fetch_data(prefix: str, user_id: int, connection: CouchDBConnection | None = None):
    """ Retrieve data from couchdb for given stat type and user.

    For each stat type, a database is created daily. We do not have a way to do this atomically so the latest
    database for a type may be incomplete when we query it. So, query all databases for given stat 1 by 1 in
    descending order of their creation until user data is found.

    Args:
         prefix: the string to match database names with
         user_id: the user to retrieve data for
         connection: the couchdb instance to query, defaults to the one configured via ``init``
    """
    connection = _get_connection(connection)
    databases = list_databases(prefix, connection=connection)

    for database in databases:
        document_url = f"{connection.get_database_url(database)}/{user_id}"
        response = requests.get(document_url)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        return response.json()

    return None


def fetch_exact_data(database: str, document_id: str, connection: CouchDBConnection | None = None):
    """ Retrieve data from couchdb for the exact given database and document id.
    Args:
         database: the database name to retrieve data from
         document_id: the document_id to retrieve data for
         connection: the couchdb instance to query, defaults to the one configured via ``init``
    """
    document_url = f"{_get_connection(connection).get_database_url(database)}/{document_id}"
    response = requests.get(document_url)
    if response.status_code == 404:
        return None
    return response.json()


def insert_data(database: str, data: list[dict]):
    """ Insert the given data into the specified database. """
    with start_span(op="serializing", name="serialize data to json"):
        docs = orjson.dumps({"docs": data})

    with start_span(op="http", name="insert docs in couchdb using api"):
        couchdb_url = f"{_get_database_url(database)}/_bulk_docs"
        response = requests.post(couchdb_url, data=docs, headers={"Content-Type": "application/json"})
        response.raise_for_status()

    with start_span(op="deserializing", name="checking response for conflicts"):
        conflict_doc_ids = []
        for doc_status in response.json():
            if doc_status.get("error") == "conflict":
                conflict_doc_ids.append(doc_status["id"])

        if not conflict_doc_ids:
            return

        conflict_docs = orjson.dumps({"docs": [{"id": doc_id} for doc_id in conflict_doc_ids]})

    with start_span(op="http", name="retrieving conflicts from database"):
        response = requests.post(
            f"{_get_database_url(database)}/_bulk_get",
            data=conflict_docs,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

    with start_span(op="deserializing", name="processing conflicting revisions"):
        revs_map = {}
        for result in response.json()["results"]:
            existing_doc = result["docs"][0]["ok"]
            revs_map[existing_doc["_id"]] = existing_doc["_rev"]

        docs_to_update = []
        for doc in data:
            if doc["_id"] in revs_map:
                doc["_rev"] = revs_map[doc["_id"]]
            docs_to_update.append(doc)

    with start_span(op="serializing", name="serialize conflicting docs to update"):
        docs_to_update = orjson.dumps({"docs": docs_to_update})

    with start_span(op="http", name="retry updating conflicts in database"):
        response = requests.post(couchdb_url, data=docs_to_update, headers={"Content-Type": "application/json"})
        response.raise_for_status()


def try_insert_data(database: str, data: list[dict]):
    """ Try to insert data in the database if it exists, otherwise create the database and try again. """
    try:
        insert_data(database, data)
    except Exception:
        create_database(database)
        insert_data(database, data)


def delete_data(database: str, doc_id: int | str):
    """ Delete the given document from couchdb database.

    Once a document is deleted, it will return a 404 if someone tries to fetch it afterwards. However,
    the document will still remain in the database. To actually remove the document from the database,
    look for the purge endpoint in couchdb docs.

    Args:
         database: the database to delete data from
         doc_id: the id of the document to delete
    """
    document_url = f"{_get_database_url(database)}/{doc_id}"
    response = requests.head(document_url)
    response.raise_for_status()

    rev = json.loads(response.headers.get("ETag"))
    response = requests.delete(document_url, params={"rev": rev})
    response.raise_for_status()


def check_database_lock(database: str):
    """ Checks whether a database is "currently locked" by checking the existence of
     DATABASE_LOCK_FILE. A database is usually locked only during dumps.
    """
    url = f"{_get_database_url(database)}/{DATABASE_LOCK_FILE}"
    response = requests.get(url)
    return response.status_code == 200


def lock_database(database: str):
    """ 'Lock' the database so that it does not get deleted.

        Note that, this is not a couchdb feature but a way we made up to co-ordinate process in LB.
        The onus is the on other users to check for existence of the LOCK file before deleting a
        database.
    """
    document_url = f"{_get_database_url(database)}/{DATABASE_LOCK_FILE}"
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
        allowed_methods=["HEAD", "GET", "OPTIONS"]
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
    # check if the database is already locked from a previous failed dump attempt
    if not check_database_lock(database):
        lock_database(database)

    try:
        with _get_requests_session() as http:
            database_url = _get_database_url(database)
            response = http.get(database_url)
            total_docs = response.json()["doc_count"]

            all_docs_url = f"{database_url}/_all_docs"

            startkey_docid = None
            limit = 50
            for skip in range(0, total_docs, limit):
                params = {
                    "limit": limit,
                    "include_docs": True
                }
                if startkey_docid is not None:
                    params["startkey_docid"] = startkey_docid
                    params["skip"] = 1
                response = http.get(all_docs_url, params=params)

                rows = orjson.loads(response.content)["rows"]
                for row in rows:
                    doc = row["doc"]
                    startkey_docid = doc.pop("_id", None)
                    doc.pop("key", None)
                    doc.pop("_rev", None)
                    doc.pop("_revisions", None)

                    if not doc:
                        continue

                    fp.write(orjson.dumps(doc, option=orjson.OPT_APPEND_NEWLINE))
    finally:
        unlock_database(database)
