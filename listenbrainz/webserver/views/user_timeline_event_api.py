# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2021 Param Singh <me@param.codes>
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

import pydantic
from typing import Optional
import ujson

from flask import Blueprint, jsonify, request

import listenbrainz.db.user_timeline_event as db_user_timeline_event

from data.model.user_timeline_event import RecordingRecommendationMetadata
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APIUnauthorized
from listenbrainz.webserver.views.api_tools import validate_auth_header
from listenbrainz.webserver.rate_limiter import ratelimit

user_timeline_event_api_bp = Blueprint('user_timeline_event_api_bp', __name__)


@user_timeline_event_api_bp.route('/user/<user_name>/timeline-event/create/recording', methods=['POST', 'OPTIONS'])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def create_user_recording_recommendation_event(user_name):
    """ Make the user recommend a recording to their followers.

    The request should post the following data about the recording being recommended::

        {
            "metadata": {
                "artist_name": <The name of the artist, required>,
                "track_name": <The name of the track, required>,
                "artist_msid": <The MessyBrainz ID of the artist, required>,
                "recording_msid": <The MessyBrainz ID of the recording, required>,
                "release_name": <The name of the release, optional>
                "recording_mbid": <The MusicBrainz ID of the recording, optional>
            }
        }


    :param user_name: The MusicBrainz ID of the user who is recommending the recording.
    :type user_name: ``str``
    :statuscode 200: Successful query, recording has been recommended!
    :statuscode 400: Bad request, check ``response['error']`` for more details.
    :statuscode 401: Unauthorized, you do not have permissions to recommend recordings on the behalf of this user
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()
    if user_name != user['musicbrainz_id']:
        raise APIUnauthorized("You don't have permissions to post to this user's timeline.")

    try:
        data = ujson.loads(request.get_data())
    except ValueError as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    try:
        metadata = RecordingRecommendationMetadata(**data['metadata'])
    except pydantic.ValidationError as e:
        raise APIBadRequest(f"Invalid metadata: {str(e)}")

    try:
        event = db_user_timeline_event.create_user_track_recommendation_event(user['id'], metadata)
    except DatabaseException:
        raise APIInternalServerError("Something went wrong, please try again.")


    event_data = event.dict()
    event_data['created'] = event_data['created'].timestamp()
    event_data['event_type'] = event_data['event_type'].value
    return jsonify(event_data)
