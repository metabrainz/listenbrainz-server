from listenbrainz.db import couchdb


def insert_recent_releases(database, docs):
    for doc in docs:
        doc["_id"] = str(doc["user_id"])
    couchdb.insert_data(database, docs)


def get_recent_releases(user_id):
    data = couchdb.fetch_data("fresh_releases", user_id)
    if not data:
        return None
    return {
        "user_id": user_id,
        "releases": data["releases"]
    }
