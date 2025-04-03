# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2020 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import listenbrainz.db.user as db_user
import listenbrainz.db.missing_musicbrainz_data as db_missing_musicbrainz_data
from listenbrainz.webserver import ts_conn, db_conn

from listenbrainz.webserver.errors import APIBadRequest, APINotFound, APINoContent
from listenbrainz.webserver.views.api_tools import (DEFAULT_ITEMS_PER_GET,
                                                    get_non_negative_param,
                                                    MAX_ITEMS_PER_GET)

from flask import Blueprint, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from brainzutils.ratelimit import ratelimit

missing_musicbrainz_data_api_bp = Blueprint('missing_musicbrainz_data_v1', __name__)


@missing_musicbrainz_data_api_bp.get("/user/<user_name>/")
@crossdomain
@ratelimit()
def get_missing_musicbrainz_data(user_name):
    """ Get musicbrainz data sorted on "listened_at" that the user has submitted to ListenBrainz but has not
        submitted to MusicBrainz.

        A sample response from the endpoint may look like:

        .. code-block:: json

            {
                "payload":
                {
                    "last_updated": 1588494361,
                    "data": [
                        {
                            "artist_name": "Red City Radio",
                            "listened_at": "2020-04-29 23:40:47",
                            "recording_msid": "78f63ece-86e1-48bf-a7ff-29793d4a84e6",
                            "release_name": "The Dangers Of Standing Still",
                            "track_name": "Never Bring A Cup Of Water To A Gunfight"
                        },
                        {
                            "artist_name": "Red City Radio",
                            "listened_at": "2020-04-29 23:37:57",
                            "recording_msid": "d226200a-a9be-4e9e-9f7c-d74a71647893",
                            "release_name": "The Dangers Of Standing Still",
                            "track_name": "Nathaniel Martinez"
                        }
                    ],
                    "count": 2,
                    "offset": 4,
                    "total_data_count": 25,
                    "user_name": "Vansika"
                }
            }

        :param count: Optional, number of records to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
            Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
        :type count: ``int``

        :param offset: Optional, number of records to skip from the beginning, for pagination.
            Ex. An offset of 5 means the 5 records will be skipped, defaults to 0
        :type offset: ``int``

        :statuscode 200: Successful query, you have data!
        :statuscode 400: Bad request, check ``response['error']`` for more details
        :statuscode 404: User not found.
        :statuscode 204: Missing MusicBrainz data for the user not calculated , empty response will be returned
    """
    # source indicates the *source* script/algorithm by which the missing musicbrainz data was calculated.
    # The source may change in future
    source = 'cf'

    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    count = min(count, MAX_ITEMS_PER_GET)

    data, created = db_missing_musicbrainz_data.get_user_missing_musicbrainz_data(db_conn, ts_conn, user['id'], source)

    if not data:
        err_msg = 'Missing MusicBrainz data for {} not calculated or none exists.'.format(user_name)
        raise APINoContent(err_msg)

    missing_musicbrainz_data_list_filtered = data[offset:count]

    payload = {
        'payload': {
            'user_name': user_name,
            'last_updated': int(created.timestamp()),
            'count': len(missing_musicbrainz_data_list_filtered),
            'total_data_count': len(data),
            'offset': offset,
            'data': missing_musicbrainz_data_list_filtered
        }
    }

    return jsonify(payload)
