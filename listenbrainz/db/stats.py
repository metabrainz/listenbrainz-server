"""This module contains functions to insert and retrieve statistics
   calculated from Apache Spark into the database.
"""

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2017 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


from datetime import datetime
from typing import Optional

import orjson
from flask import current_app
from pydantic import ValidationError
from requests import HTTPError
from sentry_sdk import start_span

from data.model.common_stat import StatApi
from listenbrainz.db import couchdb
from listenbrainz.db.couchdb import try_insert_data
from listenbrainz.db.user import get_users_by_id

# sitewide statistics are stored in the user statistics table
# as statistics for a special user with the following user_id.
# Note: this is the id from LB's "user" table and *not musicbrainz_row_id*.
SITEWIDE_STATS_USER_ID = 15753
SITEWIDE_STATS_DB = "sitewide_stats_current"


def insert(database: str, from_ts: int, to_ts: int, values: list[dict], key="user_id"):
    """ Insert stats in couchdb.

        Args:
            database: the name of the database to insert the stat in
            from_ts: the start of the time period for which the stat is
            to_ts: the end of the time period for which the stat is
            values: list with each item as stat for 1 user
            key: the key of the value to user as _id of the document
    """
    with start_span(op="processing", name="add _id, from_ts, to_ts and last_updated to docs"):
        for doc in values:
            doc["_id"] = str(doc[key])
            doc["key"] = doc[key]
            doc["from_ts"] = from_ts
            doc["to_ts"] = to_ts
            doc["last_updated"] = int(datetime.now().timestamp())

    couchdb.insert_data(database, values)


def get(user_id, stats_type, stats_range, stats_model) -> Optional[StatApi]:
    """ Retrieve stats for the given user, stats range and stats type.

        Args:
            user_id: ListenBrainz id of the user
            stats_range: time period to retrieve stats for
            stats_type: the stat to retrieve
            stats_model: the pydantic model for the stats
    """
    prefix = f"{stats_type}_{stats_range}"
    try:
        data = couchdb.fetch_data(prefix, user_id)
        if data is not None:
            return StatApi[stats_model](
                user_id=user_id,
                from_ts=data["from_ts"],
                to_ts=data["to_ts"],
                count=data.get("count"),  # all stats may not have a count field
                stats_range=stats_range,
                data=data["data"],
                last_updated=data["last_updated"]
            )
    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)
    except (ValidationError, KeyError) as e:
        current_app.logger.error(
            f"{e}. Occurred while processing {stats_range} {stats_type} for user_id: {user_id}"
            f" and data: {orjson.dumps(data, option=orjson.OPT_INDENT_2).decode('utf-8')}", exc_info=True)
    except Exception as e:
        current_app.logger.error(f"Error connecting to CouchDB: {e}")

    return None


def get_entity_listener(db_conn, entity, entity_id, stats_range) -> Optional[dict]:
    """ Retrieve stats for the given entity, stats range and stats type.

        Args:
            db_conn: database connection
            entity: the type of stat entity
            entity_id: the mbid of the particular entity item
            stats_range: time period to retrieve stats for
    """
    prefix = f"{entity}_listeners_{stats_range}"
    try:
        doc = couchdb.fetch_data(prefix, entity_id)
        if doc is None:
            return None

        doc.pop("_id", None)
        doc.pop("key", None)
        doc.pop("_rev", None)
        doc.pop("_revisions", None)

        user_id_listeners = doc.pop("listeners", [])
        users_map = get_users_by_id(db_conn, [x["user_id"] for x in user_id_listeners])
        user_name_listeners = []
        for x in user_id_listeners:
            user_name = users_map.get(x["user_id"])
            if user_name:
                user_name_listeners.append({"user_name": user_name, "listen_count": x["listen_count"]})

        doc["stats_range"] = stats_range
        doc["listeners"] = user_name_listeners
        return doc
    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)
    except (ValidationError, KeyError) as e:
        current_app.logger.error(
            f"{e}. Occurred while processing {stats_range} {entity} for mbid: {entity_id}"
            f" and data: {orjson.dumps(doc, option=orjson.OPT_INDENT_2).decode('utf-8')}", exc_info=True)
    except Exception as e:
        current_app.logger.error(f"Error connecting to CouchDB: {e}")
    return None


def insert_sitewide_stats(stats_type: str, stats_range: str, from_ts: int, to_ts: int, data: dict):
    """ Insert sitewide stats in couchdb.

        Args:
            database: the name of the database to insert the stat in
            from_ts: the start of the time period for which the stat is
            to_ts: the end of the time period for which the stat is
            data: sitewide stat to insert
    """
    data["_id"] = f"{stats_type}_{stats_range}"
    data["key"] = data["_id"]
    data["user_id"] = SITEWIDE_STATS_USER_ID
    data["from_ts"] = from_ts
    data["to_ts"] = to_ts
    data["last_updated"] = int(datetime.now().timestamp())

    try_insert_data(SITEWIDE_STATS_DB, [data])


def get_sitewide_stats(type_: str, stats_range: str):
    """ Retrieve sitewide stats for a given type and range. """
    return couchdb.fetch_exact_data(SITEWIDE_STATS_DB, f"{type_}_{stats_range}")
