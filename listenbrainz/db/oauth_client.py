""" Read only access to the OAuth applications registered with MetaBrainz.

The table lives in the MetaBrainz database (see metabrainz.org, ``metabrainz/model/oauth/
client.py``), so everything here goes through ``meb_conn`` rather than the ListenBrainz
connection, and is only usable when SQLALCHEMY_METABRAINZ_URI is configured.
"""

from typing import Optional

import sqlalchemy


def get_client_name(meb_conn, client_id: str) -> Optional[str]:
    """ Return the name the owner of an OAuth client registered it under.

    Args:
        meb_conn: a connection to the MetaBrainz database
        client_id: the client id, as returned by the introspection endpoint

    Returns: the name of the application, or None if there is no such client.
    """
    result = meb_conn.execute(sqlalchemy.text("""
        SELECT name
          FROM oauth.client
         WHERE client_id = :client_id
    """), {"client_id": client_id})
    row = result.fetchone()
    return row.name if row else None
