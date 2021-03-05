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
import time
import ujson

from collections import defaultdict
from typing import Optional, List
from flask import Blueprint, jsonify, request, current_app

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import listenbrainz.db.user_timeline_event as db_user_timeline_event

from data.model.listen import APIListen, TrackMetadata, AdditionalInfo
from data.model.user_timeline_event import RecordingRecommendationMetadata, APITimelineEvent, UserTimelineEventType, APIFollowEvent
from listenbrainz import webserver
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.listenstore import TimescaleListenStore
from listenbrainz.webserver.views.api import _validate_get_endpoint_params
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


@user_timeline_event_api_bp.route('/user/<user_name>/feed/events', methods=['OPTIONS', 'GET'])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def user_feed(user_name: str):
    user = validate_auth_header()
    if user_name != user['musicbrainz_id']:
        raise APIUnauthorized("You don't have permissions to view this user's timeline.")

    db_conn = webserver.create_timescale(current_app)
    min_ts, max_ts, count, time_range = _validate_get_endpoint_params(db_conn, user_name)
    if min_ts is None and max_ts is None:
        max_ts = int(time.time())

    users_following = db_user_relationship.get_following_for_user(user['id'])

    # get all listen events
    musicbrainz_ids = [user['musicbrainz_id'] for user in users_following]
    listen_events = get_listen_events(db_conn, musicbrainz_ids, min_ts, max_ts, count, time_range)

    follow_events = get_follow_events(
        user_ids=(user['id'] for user in users_following),
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )

    recording_recommendation_events = get_recording_recommendation_events(
        users_following=users_following,
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )

    all_events = sorted([listen_events + follow_events + recording_recommendation_events], key=lambda event: event.created)

    # sadly, we need to serialize the event_type ourselves, otherwise, jsonify converts it badly
    for index, event in enumerate(all_events):
        all_events[index].event_type = event.event_type.value

    all_events = all_events[:count]

    return jsonify({'payload': {
        'count': len(all_events),
        'events': all_events.dict(),
    }})


def get_listen_events(
    db_conn: TimescaleListenStore,
    musicbrainz_ids: List[str],
    min_ts: int,
    max_ts: int,
    count: int,
    time_range: int,
) -> List[APITimelineEvent]:
    """ Gets all listen events in the feed.
    """

    # NOTE: For now, we get a bunch of listens for the users the current
    # user is following and take a max of 2 out of them per user. This
    # could be done better to get the latest 2 listens for each user,
    # but I'm happy with this heuristic for now and we can change later.
    db_conn = webserver.create_timescale(current_app)
    listens = db_conn.fetch_listens_for_multiple_users_from_storage(
        musicbrainz_ids,
        limit=count,
        from_ts=min_ts,
        to_ts=max_ts,
        time_range=time_range,
        order=1,  # descending
    )

    user_listens_map = defaultdict(list)
    for listen in listens:
        if len(user_listens_map[listen.user_name]) < 2:
            user_listens_map[listen.user_name].append(listen)

    events = []
    for user in user_listens_map:
        for listen in user_listens_map[user]:
            listen = APIListen(**listen.to_api())
            events.append(APITimelineEvent(
                event_type=UserTimelineEventType.LISTEN,
                user_name=listen.user_name,
                created=listen.listend_at,
                metadata=listen,
            ))
    return events


def get_follow_events(user_ids: List[int], min_ts: int, max_ts: int, count: int) -> List[APITimelineEvent]:
    follow_events_db = db_user_relationship.get_follow_events(
        user_ids=user_ids,
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )

    events = []
    for event in follow_events_db:
        follow_event = APIFollowEvent(
            user_name_0=event['user_name_0'],
            user_name_1=event['user_name_1'],
            type='follow',
            created=event['created'].timestamp(),
        )
        events.append(APITimelineEvent(
            event_type=UserTimelineEventType.FOLLOW,
            user_name=follow_event.user_name_0,
            created=follow_event.created,
            metadata=follow_event,
        ))
    return events

def get_recording_recommendation_events(users_following: List[dict], min_ts: int, max_ts: int, count: int) -> List[APITimelineEvent]:
    id_username_map = {user['id']: user['musicbrainz_id'] for user in users_following}
    recording_recommendation_events_db = db_user_timeline_event.get_recording_recommendation_events_for_feed(
        user_ids=(user['id'] for user in users_following),
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )

    events = []
    for event in recording_recommendation_events_db:
        listen = APIListen(
            user_name=id_username_map[event['user_id']],
            track_metadata=TrackMetadata(
                artist_name=event['metadata']['artist_name'],
                track_name=event['metadata']['track_name'],
                release_name=event['metadata']['release_name'],
                additional_info=AdditionalInfo(
                    recording_msid=event['metadata']['recording_msid'],
                    recording_mbid=event['metadata']['recording_mbid'],
                    artist_msid=event['metadata']['artist_msid'],
                )
            ),
        )

        events.append(APITimelineEvent(
            event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
            user_name=listen.user_name,
            created=event['created'].timestamp(),
            metadata=listen,
        ))
    return events
