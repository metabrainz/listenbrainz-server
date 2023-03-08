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
import logging

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Iterable

import pydantic
import orjson
from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, request, current_app

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import listenbrainz.db.user_timeline_event as db_user_timeline_event
from data.model.listen import APIListen, TrackMetadata, AdditionalInfo
from listenbrainz.db.model.user_timeline_event import RecordingRecommendationMetadata, APITimelineEvent, UserTimelineEventType, \
    APIFollowEvent, NotificationMetadata, APINotificationEvent, APIPinEvent, APICBReviewEvent, \
    CBReviewTimelineMetadata, PersonalRecordingRecommendationMetadata, APIPersonalRecommendationEvent
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.db.model.review import CBReviewMetadata
from listenbrainz.db.pinned_recording import get_pins_for_feed, get_pin_by_id
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService
from listenbrainz.webserver import timescale_connection
from listenbrainz.webserver.decorators import crossdomain, api_listenstore_needed
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APIUnauthorized, APINotFound, \
    APIForbidden
from listenbrainz.webserver.views.api_tools import validate_auth_header, _filter_description_html, \
    _validate_get_endpoint_params

MAX_LISTEN_EVENTS_PER_USER = 2  # the maximum number of listens we want to return in the feed per user
MAX_LISTEN_EVENTS_OVERALL = 10  # the maximum number of listens we want to return in the feed overall across users
DEFAULT_LISTEN_EVENT_WINDOW = 14 * 24 * 60 * 60  # 14 days, to limit the search space of listen events and avoid timeouts

user_timeline_event_api_bp = Blueprint('user_timeline_event_api_bp', __name__)


@user_timeline_event_api_bp.route('/user/<user_name>/timeline-event/create/recording', methods=['POST', 'OPTIONS'])
@crossdomain
@ratelimit()
def create_user_recording_recommendation_event(user_name):
    """ Make the user recommend a recording to their followers.

    The request should post the following data about the recording being recommended:

    .. code-block:: json

        {
            "metadata": {
                "artist_name": "<The name of the artist, required>",
                "track_name": "<The name of the track, required>",
                "recording_msid": "<The MessyBrainz ID of the recording, required>",
                "release_name": "<The name of the release, optional>",
                "recording_mbid": "<The MusicBrainz ID of the recording, optional>"
            }
        }

    :param user_name: The MusicBrainz ID of the user who is recommending the recording.
    :type user_name: ``str``
    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
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
        data = orjson.loads(request.get_data())
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


@user_timeline_event_api_bp.route('/user/<user_name>/timeline-event/create/notification', methods=['POST', 'OPTIONS'])
@crossdomain
@ratelimit()
def create_user_notification_event(user_name):
    """ Post a message with a link on a user's timeline. Only approved users are allowed to perform this action.

    The request should contain the following data:

    .. code-block:: json

        {
            "metadata": {
                "message": "<the message to post, required>",
            }
        }

    :param user_name: The MusicBrainz ID of the user on whose timeline the message is to be posted.
    :type user_name: ``str``
    :statuscode 200: Successful query, message has been posted!
    :statuscode 400: Bad request, check ``response['error']`` for more details.
    :statuscode 403: Forbidden, you are not an approved user.
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    creator = validate_auth_header()
    if creator["musicbrainz_id"] not in current_app.config['APPROVED_PLAYLIST_BOTS']:
        raise APIForbidden("Only approved users are allowed to post a message on a user's timeline.")

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound(f"Cannot find user: {user_name}")

    try:
        data = orjson.loads(request.get_data())['metadata']
    except (ValueError, KeyError) as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    if "message" not in data:
        raise APIBadRequest("Invalid metadata: message is missing")

    # Not filtering html in the message because only approved users can use this endpoint.
    # if this changes in the future, add back html cleanup here.
    message = data["message"]
    metadata = NotificationMetadata(creator=creator['musicbrainz_id'], message=message)

    try:
        event = db_user_timeline_event.create_user_notification_event(user['id'], metadata)
    except DatabaseException:
        raise APIInternalServerError("Something went wrong, please try again.")

    event_data = event.dict()
    event_data['created'] = event_data['created'].timestamp()
    event_data['event_type'] = event_data['event_type'].value
    return jsonify(event_data)


@user_timeline_event_api_bp.route('/user/<user_name>/timeline-event/create/review', methods=['POST', 'OPTIONS'])
@crossdomain
@ratelimit()
def create_user_cb_review_event(user_name):
    """ Creates a CritiqueBrainz review event for the user. This also creates a corresponding review in
    CritiqueBrainz. Users need to have linked their ListenBrainz account with CritiqueBrainz first to use
    this endpoint successfully.

    The request should contain the following data:

    .. code-block:: json

        {
            "metadata": {
                "message": "<the message to post, required>",
            }
        }

    :param user_name: The MusicBrainz ID of the user who is creating the review.
    :type user_name: ``str``
    :statuscode 200: Successful query, message has been posted!
    :statuscode 400: Bad request, check ``response['error']`` for more details.
    :statuscode 403: Forbidden, you have not linked with a CritiqueBrainz account.
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()
    if user_name != user["musicbrainz_id"]:
        raise APIUnauthorized("You don't have permissions to post to this user's timeline.")

    try:
        data = orjson.loads(request.get_data())
    except ValueError as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    try:
        metadata = data["metadata"]
        review = CBReviewMetadata(
            name=metadata["entity_name"],
            entity_id=metadata["entity_id"],
            entity_type=metadata["entity_type"],
            text=metadata["text"],
            language=metadata["language"],
            rating=metadata.get("rating")
        )
    except (pydantic.ValidationError, KeyError):
        raise APIBadRequest(f"Invalid metadata: {str(data)}")

    review_id = CritiqueBrainzService().submit_review(user["id"], review)
    metadata = CBReviewTimelineMetadata(
        review_id=review_id,
        entity_id=review.entity_id,
        entity_name=review.name
    )
    event = db_user_timeline_event.create_user_cb_review_event(user["id"], metadata)

    event_data = event.dict()
    event_data["created"] = event_data["created"].timestamp()
    event_data["event_type"] = event_data["event_type"].value
    return jsonify(event_data)


@user_timeline_event_api_bp.route('/user/<user_name>/feed/events', methods=['OPTIONS', 'GET'])
@crossdomain
@ratelimit()
@api_listenstore_needed
def user_feed(user_name: str):
    """ Get feed events for a user's timeline.

    :param user_name: The MusicBrainz ID of the user whose timeline is being requested.
    :type user_name: ``str``
    :param max_ts: If you specify a ``max_ts`` timestamp, events with timestamps less than the value will be returned
    :param min_ts: If you specify a ``min_ts`` timestamp, events with timestamps greater than the value will be returned
    :param count: Optional, number of events to return. Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` . Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successful query, you have feed events!
    :statuscode 400: Bad request, check ``response['error']`` for more details.
    :statuscode 401: Unauthorized, you do not have permission to view this user's feed.
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header()
    if user_name != user['musicbrainz_id']:
        raise APIUnauthorized("You don't have permissions to view this user's timeline.")

    min_ts, max_ts, count = _validate_get_endpoint_params()
    if min_ts is None and max_ts is None:
        max_ts = int(time.time())

    users_following = db_user_relationship.get_following_for_user(user['id'])

    # get all listen events
    if len(users_following) == 0:
        listen_events = []
    else:
        listen_events = get_listen_events(users_following, min_ts, max_ts)

    # for events like "follow" and "recording recommendations", we want to show the user
    # their own events as well
    users_for_feed_events = users_following + [user]
    follow_events = get_follow_events(
        user_ids=tuple(user['id'] for user in users_for_feed_events),
        min_ts=min_ts or 0,
        max_ts=max_ts or int(time.time()),
        count=count,
    )

    recording_recommendation_events = get_recording_recommendation_events(
        users_for_events=users_for_feed_events,
        min_ts=min_ts or 0,
        max_ts=max_ts or int(time.time()),
        count=count,
    )

    personal_recording_recommendation_events = get_personal_recording_recommendation_events(
        user=user,
        min_ts=min_ts or 0,
        max_ts=max_ts or int(time.time()),
        count=count,
    )

    cb_review_events = get_cb_review_events(
        users_for_events=users_for_feed_events,
        min_ts=min_ts or 0,
        max_ts=max_ts or int(time.time()),
        count=count,
    )

    notification_events = get_notification_events(user, count)

    recording_pin_events = get_recording_pin_events(
        users_for_events=users_for_feed_events,
        min_ts=min_ts or 0,
        max_ts=max_ts or int(time.time()),
        count=count,
    )

    hidden_events = db_user_timeline_event.get_hidden_timeline_events(user['id'], count)
    hidden_events_pin = {}
    hidden_events_recommendation = {}

    for hidden_event in hidden_events:
        if hidden_event.event_type.value == UserTimelineEventType.RECORDING_RECOMMENDATION.value:
            hidden_events_recommendation[hidden_event.event_id] = hidden_event
        else:
            hidden_events_pin[hidden_event.event_id] = hidden_event

    for event in recording_recommendation_events:
        if event.id in hidden_events_recommendation:
            event.hidden = True

    for event in recording_pin_events:
        if event.id in hidden_events_pin:
            event.hidden = True

    # TODO: add playlist event and like event
    all_events = sorted(
        listen_events + follow_events + recording_recommendation_events + recording_pin_events
        + cb_review_events + notification_events + personal_recording_recommendation_events,
        key=lambda event: -event.created,
    )

    # sadly, we need to serialize the event_type ourselves, otherwise, jsonify converts it badly
    for index, event in enumerate(all_events):
        all_events[index].event_type = event.event_type.value

    all_events = all_events[:count]

    return jsonify({'payload': {
        'count': len(all_events),
        'user_id': user_name,
        'events': [event.dict() for event in all_events],
    }})


@user_timeline_event_api_bp.route("/user/<user_name>/feed/events/delete", methods=['OPTIONS', 'POST'])
@crossdomain
@ratelimit()
def delete_feed_events(user_name):
    '''
    Delete those events from user's feed that belong to them. Supports deletion of recommendation and notification.
    Along with the authorization token, post the event type and event id. For example:

    .. code-block:: json

        {
            "event_type": "recording_recommendation",
            "id": "<integer id of the event>"
        }

    .. code-block:: json

        {
            "event_type": "notification",
            "id": "<integer id of the event>"
        }

    :param user_name: The MusicBrainz ID of the user from whose timeline events are being deleted
    :type user_name: ``str``
    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successful deletion
    :statuscode 400: Bad request, check ``response['error']`` for more details.
    :statuscode 401: Unauthorized
    :statuscode 404: User not found
    :statuscode 500: API Internal Server Error
    :resheader Content-Type: *application/json*
    '''
    user = validate_auth_header()
    if user_name != user['musicbrainz_id']:
        raise APIUnauthorized("You don't have permissions to delete from this user's timeline.")

    try:
        event = orjson.loads(request.get_data())

        if event["event_type"] in [UserTimelineEventType.RECORDING_RECOMMENDATION.value,
                UserTimelineEventType.NOTIFICATION.value, UserTimelineEventType.PERSONAL_RECORDING_RECOMMENDATION.value]:
            try:
                event_deleted = db_user_timeline_event.delete_user_timeline_event(event["id"], user["id"])
            except Exception as e:
                raise APIInternalServerError("Something went wrong. Please try again")
            if not event_deleted:
                raise APINotFound("Cannot find '%s' event with id '%s' for user '%s'" % (event["event_type"], event["id"],
                    user["id"]))
            return jsonify({"status": "ok"})

        raise APIBadRequest("This event type is not supported for deletion via this method")

    except (ValueError, KeyError) as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")


@user_timeline_event_api_bp.route("/user/<user_name>/feed/events/hide", methods=['OPTIONS', 'POST'])
@crossdomain
@ratelimit()
def hide_user_timeline_event(user_name):
    '''
    Hide events from the user feed, only recording_recommendation and recording_pin
    events that have been generated by the people one is following can be deleted
    via this endpoint. For example:

    .. code-block:: json

        {
            "event_type": "recording_recommendation",
            "event_id": "<integer id of the event>"
        }

    .. code-block:: json

        {
            "event_type": "recording_pin",
            "event_id": "<integer id of the event>"
        }

    :param user_name: The MusicBrainz ID of the user from whose timeline events are being deleted
    :type user_name: ``str``
    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Event hidden successfully
    :statuscode 400: Bad request, check ``response['error']`` for more details.
    :statuscode 401: Unauthorized
    :statuscode 404: User not found
    :statuscode 500: API Internal Server Error
    :resheader Content-Type: *application/json*
    '''

    user = validate_auth_header()
    if user_name != user['musicbrainz_id']:
        raise APIUnauthorized("You don't have permissions to hide events from this user's timeline.")

    try:
        data = orjson.loads(request.get_data())
    except (ValueError, KeyError) as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    if 'event_type' not in data or 'event_id' not in data:
        raise APIBadRequest("JSON document must contain both event_type and event_id", data)

    row_id = data["event_id"]
    if data["event_type"] == UserTimelineEventType.RECORDING_RECOMMENDATION.value:
        result = db_user_timeline_event.get_user_timeline_event_by_id(row_id)
    elif data["event_type"] == UserTimelineEventType.RECORDING_PIN.value:
        result = get_pin_by_id(row_id)
    else:
        raise APIBadRequest("This event type is not supported for hiding")

    if not result:
        raise APIBadRequest(f"{data['event_type']} event with id {row_id} not found")

    if db_user_relationship.is_following_user(user['id'], result.user_id):
        db_user_timeline_event.hide_user_timeline_event(user['id'], data["event_type"], data["event_id"])
        return jsonify({"status": "ok"})
    else:
        raise APIUnauthorized("You cannot hide events of this user")


@user_timeline_event_api_bp.route("/user/<user_name>/feed/events/unhide", methods=['OPTIONS', 'POST'])
@crossdomain
@ratelimit()
def unhide_user_timeline_event(user_name):
    '''
    Delete hidden events from the user feed, aka unhide events. For example:

    .. code-block:: json

        {
            "event_type": "recording_pin",
            "event_id": "<integer id of the event>"
        }

    :type user_name: ``str``
    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Event unhidden successfully
    :statuscode 400: Bad request, check ``response['error']`` for more details.
    :statuscode 401: Unauthorized
    :statuscode 404: User not found
    :statuscode 500: API Internal Server Error
    :resheader Content-Type: *application/json*
    '''
    
    user = validate_auth_header()
    if user_name != user['musicbrainz_id']:
        raise APIUnauthorized("You don't have permissions to delete events from this user's timeline.")

    try:
        data = orjson.loads(request.get_data())
    except (ValueError, KeyError) as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    if 'event_type' not in data or 'event_id' not in data:
        raise APIBadRequest("JSON document must contain both event_type and event_id", data)

    db_user_timeline_event.unhide_timeline_event(user['id'], data['event_type'], data['event_id'])
    return jsonify({"status": "ok"})


@user_timeline_event_api_bp.route('/user/<user_name>/timeline-event/create/recommend-personal', methods=['POST', 'OPTIONS'])
@crossdomain
@ratelimit()
def create_personal_recommendation_event(user_name):
    '''
    Make the user recommend a recording to their followers.
    The request should post the following data about the recording being
    recommended, and also the list of followers getting recommended:

    .. code-block:: json

        {
            "metadata": {
                "artist_name": "<The name of the artist, required>",
                "track_name": "<The name of the track, required>",
                "recording_msid": "<The MessyBrainz ID of the recording, required>",
                "release_name": "<The name of the release, optional>",
                "recording_mbid": "<The MusicBrainz ID of the recording, optional>",
                "users": [<usernames of the persons you want to recommend to, required>]
                "blurb_content": "<String containing personalized recommendation>"
            }
        }

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successful query, recording has been recommended!
    :statuscode 400: Bad request, check ``response['error']`` for more
    details.
    :statuscode 401: Unauthorized, you do not have permissions to recommend
    personal recordings on the behalf of this user
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    '''
    
    user = validate_auth_header()

    if user_name != user['musicbrainz_id']:
        raise APIUnauthorized("You don't have permissions to post to this user's timeline.")

    try:
        data = orjson.loads(request.get_data())
    except ValueError as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    metadata = data['metadata']

    try:
        metadata = PersonalRecordingRecommendationMetadata(**metadata)
        follower_results = db_user_relationship.multiple_users_by_username_following_user(user['id'], metadata.users)
        non_followers = []
        for follower in metadata.users:
            if not follower_results or not follower_results[follower]:
                non_followers.append(follower)
        if non_followers:
            raise APIBadRequest(f"You cannot recommend tracks to non-followers! These people don't follow you {str(non_followers)}")
        event = db_user_timeline_event.create_personal_recommendation_event(user['id'], metadata)
    except pydantic.ValidationError as e:
        raise APIBadRequest(f"Invalid metadata: {str(e)}")
    except DatabaseException:
        raise APIInternalServerError("Something went wrong, please try again.")

    return jsonify({"status": "ok"})


def get_listen_events(
    users: List[Dict],
    min_ts: int,
    max_ts: int,
) -> List[APITimelineEvent]:
    """ Gets all listen events in the feed.
    """
    # to avoid timeouts while fetching listen events, we want to make
    # sure that both min_ts and max_ts are defined. if only one of those
    # is set, calculate the other from it using a default window length.
    # if neither is set, use current time as max_ts and subtract window
    # length to get min_ts.
    if not min_ts and max_ts:
        min_ts = max_ts - DEFAULT_LISTEN_EVENT_WINDOW
    elif min_ts and not max_ts:
        max_ts = min_ts + DEFAULT_LISTEN_EVENT_WINDOW
    elif not min_ts and not max_ts:
        max_ts = int(datetime.now().timestamp())
        min_ts = max_ts - DEFAULT_LISTEN_EVENT_WINDOW

    listens = timescale_connection._ts.fetch_recent_listens_for_users(
        users,
        min_ts=min_ts,
        max_ts=max_ts,
        per_user_limit=MAX_LISTEN_EVENTS_PER_USER,
        limit=MAX_LISTEN_EVENTS_OVERALL
    )

    events = []
    for listen in listens:
        try:
            listen_dict = listen.to_api()
            api_listen = APIListen(**listen_dict)
            events.append(APITimelineEvent(
                event_type=UserTimelineEventType.LISTEN,
                user_name=api_listen.user_name,
                created=api_listen.listened_at,
                metadata=api_listen,
                hidden=False
            ))
        except pydantic.ValidationError as e:
            current_app.logger.error('Validation error: ' + str(e), exc_info=True)
            continue
    return events


def get_follow_events(user_ids: Tuple[int], min_ts: int, max_ts: int, count: int) -> List[APITimelineEvent]:
    """ Gets all follow events in the feed.
    """
    follow_events_db = db_user_relationship.get_follow_events(
        user_ids=user_ids,
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )

    events = []
    for event in follow_events_db:
        try:
            follow_event = APIFollowEvent(
                user_name_0=event['user_name_0'],
                user_name_1=event['user_name_1'],
                relationship_type='follow',
                created=event['created'].timestamp(),
            )
            events.append(APITimelineEvent(
                event_type=UserTimelineEventType.FOLLOW,
                user_name=follow_event.user_name_0,
                created=follow_event.created,
                metadata=follow_event,
                hidden=False
            ))
        except pydantic.ValidationError as e:
            current_app.logger.error('Validation error: ' + str(e), exc_info=True)
            continue
    return events


def get_notification_events(user: dict, count: int) -> List[APITimelineEvent]:
    """ Gets notification events for the user in the feed."""
    notification_events_db = db_user_timeline_event.get_user_notification_events(user_id=user['id'], count=count)
    events = []
    for event in notification_events_db:
        events.append(APITimelineEvent(
            id=event.id,
            event_type=UserTimelineEventType.NOTIFICATION,
            user_name=event.metadata.creator,
            created=event.created.timestamp(),
            metadata=APINotificationEvent(message=event.metadata.message),
            hidden=False
        ))
    return events


def get_recording_recommendation_events(
    users_for_events: Iterable[dict],
    min_ts: int,
    max_ts: int,
    count: int
) -> List[APITimelineEvent]:
    """ Gets all recording recommendation events in the feed. """

    id_username_map = {user['id']: user['musicbrainz_id'] for user in users_for_events}
    recording_recommendation_events_db = db_user_timeline_event.get_recording_recommendation_events_for_feed(
        user_ids=(user['id'] for user in users_for_events),
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )

    events = []
    for event in recording_recommendation_events_db:
        try:
            listen = APIListen(
                user_name=id_username_map[event.user_id],
                track_metadata=TrackMetadata(
                    artist_name=event.metadata.artist_name,
                    track_name=event.metadata.track_name,
                    release_name=event.metadata.release_name,
                    additional_info=AdditionalInfo(
                        recording_msid=event.metadata.recording_msid,
                        recording_mbid=event.metadata.recording_mbid,
                    )
                ),
            )

            events.append(APITimelineEvent(
                id=event.id,
                event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
                user_name=listen.user_name,
                created=event.created.timestamp(),
                metadata=listen,
                hidden=False,
            ))
        except pydantic.ValidationError as e:
            current_app.logger.error('Validation error: ' + str(e), exc_info=True)
            continue
    return events


def get_cb_review_events(users_for_events: List[dict], min_ts: int, max_ts: int, count: int) -> List[APITimelineEvent]:
    """ Gets all CritiqueBrainz review events in the feed.
    """
    id_username_map = {user["id"]: user["musicbrainz_id"] for user in users_for_events}
    cb_review_events_db = db_user_timeline_event.get_cb_review_events(
        user_ids=[user["id"] for user in users_for_events],
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )

    review_ids, review_id_event_map = [], {}
    for event in cb_review_events_db:
        review_id = event.metadata.review_id
        review_ids.append(review_id)
        review_id_event_map[review_id] = event

    reviews = CritiqueBrainzService().fetch_reviews(review_ids)
    if reviews is None:
        return []

    api_events = []
    for review_id, event in review_id_event_map.items():
        if review_id not in reviews:
            continue

        try:
            review_event = APICBReviewEvent(
                user_name=id_username_map[event.user_id],
                entity_id=event.metadata.entity_id,
                entity_name=event.metadata.entity_name,
                entity_type=reviews[review_id]["entity_type"],
                rating=reviews[review_id]["rating"],
                text=reviews[review_id]["text"],
                review_mbid=review_id
            )
            api_events.append(APITimelineEvent(
                id=event.id,
                event_type=UserTimelineEventType.CRITIQUEBRAINZ_REVIEW,
                user_name=review_event.user_name,
                created=event.created.timestamp(),
                metadata=review_event,
                hidden=False
            ))
        except pydantic.ValidationError as e:
            current_app.logger.error('Validation error: ' + str(e), exc_info=True)
            continue
    return api_events


def get_recording_pin_events(
    users_for_events: List[dict],
    min_ts: int,
    max_ts: int,
    count: int
) -> List[APITimelineEvent]:
    """ Gets all recording pin events in the feed."""

    id_username_map = {user['id']: user['musicbrainz_id'] for user in users_for_events}
    recording_pin_events_db = get_pins_for_feed(
        user_ids=(user['id'] for user in users_for_events),
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )
    recording_pin_events_db = fetch_track_metadata_for_items(recording_pin_events_db)

    events = []
    for pin in recording_pin_events_db:
        try:
            pinEvent = APIPinEvent(
                user_name=id_username_map[pin.user_id],
                blurb_content=pin.blurb_content,
                track_metadata=TrackMetadata(
                    artist_name=pin.track_metadata["artist_name"],
                    track_name=pin.track_metadata["track_name"],
                    release_name=None,
                    additional_info=AdditionalInfo(
                        recording_msid=pin.recording_msid,
                        recording_mbid=pin.recording_mbid,
                    )
                )
            )

            events.append(APITimelineEvent(
                id=pin.row_id,
                event_type=UserTimelineEventType.RECORDING_PIN,
                user_name=pinEvent.user_name,
                created=pin.created.timestamp(),
                metadata=pinEvent,
                hidden=False,
            ))
        except (pydantic.ValidationError, TypeError, KeyError):
            current_app.logger.error("Could not convert pinned recording to feed event", exc_info=True)
            continue
    return events


def get_personal_recording_recommendation_events(
    user: dict,
    min_ts: int,
    max_ts: int,
    count: int
) -> List[APITimelineEvent]:
    """ Gets all personal recording recommendation events in the feed.
    """

    personal_recording_recommendation_events_db = db_user_timeline_event.get_personal_recommendation_events_for_feed(
        user_id=user['id'],
        min_ts=min_ts,
        max_ts=max_ts,
        count=count,
    )

    events = []
    for event in personal_recording_recommendation_events_db:
        try:
            personal_recommendation = APIPersonalRecommendationEvent(
                artist_name=event.metadata.artist_name,
                track_name=event.metadata.track_name,
                release_name=event.metadata.release_name,
                recording_mbid=event.metadata.recording_mbid,
                recording_msid=event.metadata.recording_msid,
                users=event.metadata.users,
                blurb_content=event.metadata.blurb_content
            )

            events.append(APITimelineEvent(
                id=event.id,
                event_type=UserTimelineEventType.PERSONAL_RECORDING_RECOMMENDATION,
                user_name=event.user_name,
                created=event.created.timestamp(),
                metadata=personal_recommendation,
                hidden=False,
            ))
        except pydantic.ValidationError as e:
            current_app.logger.error('Validation error: ' + str(e), exc_info=True)
            continue
    return events
