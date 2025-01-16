import logging
from datetime import datetime
from typing import Dict, Tuple
from urllib.parse import urlparse

import bleach
import requests
from kombu.entity import PERSISTENT_DELIVERY_MODE
from more_itertools import chunked

import listenbrainz.webserver.rabbitmq_connection as rabbitmq_connection
import listenbrainz.webserver.redis_connection as redis_connection
import listenbrainz.db.user as db_user
import time
import orjson
import uuid
import sentry_sdk

from typing import NoReturn

from flask import current_app, request

from listenbrainz.listenstore import LISTEN_MINIMUM_TS
from listenbrainz.webserver import API_LISTENED_AT_ALLOWED_SKEW, db_conn
from listenbrainz.webserver.errors import APIServiceUnavailable, APIBadRequest, APIUnauthorized, \
    ListenValidationError

from listenbrainz.webserver.models import SubmitListenUserMetadata

logger = logging.getLogger(__name__)

#: Maximum overall listen size in bytes, to prevent egregious spamming.
MAX_LISTEN_SIZE = 10240

#: The maximum number of tags per listen.
MAX_TAGS_PER_LISTEN = 50

#: The maximum number of listens in a request.
MAX_LISTENS_PER_REQUEST = 1000

#: The maximum size of a payload in bytes. The same as MAX_LISTEN_SIZE * MAX_LISTENS_PER_REQUEST.
MAX_LISTEN_PAYLOAD_SIZE = MAX_LISTEN_SIZE * MAX_LISTENS_PER_REQUEST

#: The maximum length of a tag
MAX_TAG_SIZE = 64

#: The maximum number of listens returned in a single GET request.
MAX_ITEMS_PER_GET = 1000

#: The default number of listens returned in a single GET request.
DEFAULT_ITEMS_PER_GET = 25

#: The max permitted value of duration field - 24 days
MAX_DURATION_LIMIT = 24 * 24 * 60 * 60

#: The max permitted value of duration_ms field - 24 days
MAX_DURATION_MS_LIMIT = MAX_DURATION_LIMIT * 1000

MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP = 10

MAX_LISTENS_PER_RMQ_MESSAGE = 100  # internal limit on number of listens per RMQ message to avoid timeouts in TS writer


# Define the values for types of listens
LISTEN_TYPE_SINGLE = 1
LISTEN_TYPE_IMPORT = 2
LISTEN_TYPE_PLAYING_NOW = 3


def insert_payload(payload, user: SubmitListenUserMetadata, listen_type=LISTEN_TYPE_IMPORT):
    """ Convert the payload into augmented listens then submit them.
        Returns: augmented_listens
    """
    augmented_listens = _get_augmented_listens(payload, user)
    _send_listens_to_queue(listen_type, augmented_listens)
    return augmented_listens


def handle_playing_now(listen):
    """ Check that the listen doesn't already exist in redis and put it in
    there if it isn't.

    Returns:
        listen if new playing now listen, None otherwise
    """
    old_playing_now = redis_connection._redis.get_playing_now(listen['user_id'])

    track_metadata = listen['track_metadata']
    if old_playing_now and \
            listen['track_metadata']['track_name'] == old_playing_now.data['track_name'] and \
            listen['track_metadata']['artist_name'] == old_playing_now.data['artist_name']:
        return None

    listen_timeout = None
    if 'additional_info' in track_metadata:
        additional_info = track_metadata['additional_info']
        if 'duration' in additional_info:
            listen_timeout = additional_info['duration']
        elif 'duration_ms' in additional_info:
            listen_timeout = additional_info['duration_ms'] // 1000
    if listen_timeout is None:
        listen_timeout = current_app.config['PLAYING_NOW_MAX_DURATION']
    redis_connection._redis.put_playing_now(listen['user_id'], listen, listen_timeout)
    return listen


def _send_listens_to_queue(listen_type, listens):
    submit = []
    for listen in listens:
        if listen_type == LISTEN_TYPE_PLAYING_NOW:
            try:
                listen = handle_playing_now(listen)
                if listen:
                    submit.append(listen)
            except Exception:
                current_app.logger.error("Redis rpush playing_now write error: ", exc_info=True)
                raise APIServiceUnavailable("Cannot record playing_now at this time.")
        else:
            submit.append(listen)

    if submit:
        if listen_type == LISTEN_TYPE_PLAYING_NOW:
            exchange = rabbitmq_connection.PLAYING_NOW_EXCHANGE
        else:
            exchange = rabbitmq_connection.INCOMING_EXCHANGE

        for chunk in chunked(submit, MAX_LISTENS_PER_RMQ_MESSAGE):
            publish_data_to_queue(chunk, exchange)


def _raise_error_if_has_unicode_null(value, listen):
    if isinstance(value, str) and '\x00' in value:
        raise APIBadRequest("{} contains a unicode null".format(value), listen)


def check_for_unicode_null_recursively(listen: Dict):
    """ Checks for unicode null in all items in the dict, including inside
    nested dicts and lists."""
    for key, value in listen.items():
        if isinstance(value, dict):
            check_for_unicode_null_recursively(value)
        elif isinstance(value, list):
            for item in value:
                _raise_error_if_has_unicode_null(item, listen)
        else:
            _raise_error_if_has_unicode_null(value, listen)


def validate_listen(listen: Dict, listen_type) -> Dict:
    """Make sure that required keys are present, filled out and not too large.
    Also, check all keys for absence of unicode null which cannot be
    inserted into Postgres. The function may also mutate listens
    in place if needed."""

    if listen is None:
        raise ListenValidationError("Listen is empty and cannot be validated.")

    if listen_type in (LISTEN_TYPE_SINGLE, LISTEN_TYPE_IMPORT):
        validate_listened_at(listen)

        if "track_metadata" not in listen:
            raise ListenValidationError("JSON document must contain the key track_metadata"
                                        " at the top level.", listen)

        if len(listen) > 2:
            raise ListenValidationError("JSON document may only contain listened_at and "
                                        "track_metadata top level keys", listen)

        # check that listened_at value is greater than last.fm founding year.
        if listen['listened_at'] < LISTEN_MINIMUM_TS:
            raise ListenValidationError("Value for key listened_at is too low. listened_at timestamp "
                                        "should be greater than 1033410600 (2002-10-01 00:00:00 UTC).", listen)

    elif listen_type == LISTEN_TYPE_PLAYING_NOW:
        if "listened_at" in listen:
            raise ListenValidationError("JSON document must not contain listened_at while submitting"
                                        " playing_now.", listen)

        if "track_metadata" not in listen:
            raise ListenValidationError("JSON document must contain the key track_metadata"
                                        " at the top level.", listen)

        if len(listen) > 1:
            raise ListenValidationError("JSON document may only contain track_metadata as top level"
                                        " key when submitting playing_now.", listen)

    if listen["track_metadata"] is None:
        raise ListenValidationError("JSON document may not have track_metadata with null value.", listen)

    # Basic metadata
    validate_basic_metadata(listen, "track_name")
    validate_basic_metadata(listen, "artist_name")
    validate_basic_metadata(listen, "release_name", required=False)

    if 'additional_info' in listen['track_metadata']:
        # Tags
        if 'tags' in listen['track_metadata']['additional_info']:
            tags = listen['track_metadata']['additional_info']['tags']
            if len(tags) > MAX_TAGS_PER_LISTEN:
                raise ListenValidationError("JSON document may not contain more than %d items in "
                                            "track_metadata.additional_info.tags." % MAX_TAGS_PER_LISTEN, listen)
            for tag in tags:
                if len(tag) > MAX_TAG_SIZE:
                    raise ListenValidationError("JSON document may not contain track_metadata.additional_info.tags "
                                                "longer than %d characters." % MAX_TAG_SIZE, listen)

        # if both duration and duration_ms are given and valid, an error will be raised.
        if 'duration' in listen['track_metadata']['additional_info'] and 'duration_ms' in listen['track_metadata']['additional_info']:
            raise ListenValidationError("JSON document should not contain both duration and duration_ms.", listen)
        # check duration validity
        validate_duration_field(listen, "duration", MAX_DURATION_LIMIT)
        validate_duration_field(listen, "duration_ms", MAX_DURATION_MS_LIMIT)

        # MBIDs, both of the mbid validation methods mutate the listen payload if needed.
        single_mbid_keys = ['release_mbid', 'recording_mbid', 'release_group_mbid', 'track_mbid']
        for key in single_mbid_keys:
            validate_single_mbid_field(listen, key)
        multiple_mbid_keys = ['artist_mbids', 'work_mbids']
        for key in multiple_mbid_keys:
            validate_multiple_mbids_field(listen, key)

    # monitor performance of unicode null check because it might be a potential bottleneck
    with sentry_sdk.start_span(op="null check", name="check for unicode null in submitted listen json"):
        # If unicode null is present in the listen, postgres will raise an
        # error while trying to insert it. hence, reject such listens.
        check_for_unicode_null_recursively(listen)

    return listen


def validate_basic_metadata(listen, key, required=True):
    if key in listen["track_metadata"]:
        if not isinstance(listen["track_metadata"][key], str):
            raise ListenValidationError(f"track_metadata.{key} must be a single string.", listen)

        listen['track_metadata'][key] = listen['track_metadata'][key].strip()
        if len(listen['track_metadata'][key]) == 0:
            raise ListenValidationError(f"field track_metadata.{key} is empty.", listen)
    elif required:
        raise ListenValidationError(f"JSON document does not contain required field track_metadata.{key}.", listen)


def is_valid_uuid(u):
    if u is None:
        return False
    try:
        u = uuid.UUID(u)
        return True
    except (AttributeError, ValueError):
        return False


def _get_augmented_listens(payload, user: SubmitListenUserMetadata):
    """ Converts the payload to augmented list after adding user_id and user_name attributes """
    for listen in payload:
        listen['user_id'] = user.user_id
        listen['user_name'] = user.musicbrainz_id
    return payload


def log_raise_400(msg, data="") -> NoReturn:
    """ Helper function for logging issues with request data and showing error page.
        Logs the message and data, raises BadRequest exception which shows 400 Bad
        Request to the user.
    """

    if isinstance(data, dict):
        data = orjson.dumps(data).decode("utf-8")

    current_app.logger.debug("BadRequest: %s\nJSON: %s" % (msg, data))
    raise APIBadRequest(msg)


def validate_duration_field(listen, key, max_value):
    """ Check that the duration field is valid positive integer but less than the max permitted value """
    additional_info = listen["track_metadata"]["additional_info"]
    if key in additional_info:
        duration = additional_info[key]
        try:
            # the listen submission docs say we accept only integers for duration fields, but the current validation
            # also allows strings if those are convertible to integers. we need this to work around api_compat quirks.
            # see commit message for details.
            value = int(duration)
            if value <= 0:
                raise ListenValidationError(f"Value for {key} is invalid, should be a positive integer.", listen)
            if value > max_value:
                raise ListenValidationError(f"Value for {key} is too large, max permitted value is {max_value}", listen)
            additional_info[key] = value
        except (ValueError, TypeError):
            raise ListenValidationError(f"Value for {key} is invalid, should be a positive integer.", listen)


def validate_single_mbid_field(listen, key):
    """ Verify that mbid if present in the listen with given key is valid.
    A ValidationError is raised for invalid values of mbids.

    NOTE: If the mbid at the key is None or "", the key is dropped without
     raising an error.

    Args:
        listen: listen data
        key: the key whose mbid is to be validated
    """
    if key in listen['track_metadata']['additional_info']:
        mbid = listen['track_metadata']['additional_info'][key]
        if not mbid:  # the mbid field is None or "", hence drop the field and return
            del listen['track_metadata']['additional_info'][key]
            return

        if not is_valid_uuid(mbid):  # if the mbid is invalid raise an error
            raise ListenValidationError("%s MBID format invalid." % (key,), listen)


def validate_multiple_mbids_field(listen, key):
    """ Verify that all the mbids in the list if present in the listen with
    given key are valid. An ValidationError error is raised for if any mbid is
    invalid.

    NOTE: If an mbid in the list is None or "", it is dropped from the list
    without an error. If the key is an empty list or None, it is dropped
    without raising an error.

    Args:
        listen: listen data
        key: the key whose mbids is to be validated
    """
    if key in listen['track_metadata']['additional_info']:
        mbids = listen['track_metadata']['additional_info'][key]
        if not mbids:  # empty list or None, drop the field and return
            del listen['track_metadata']['additional_info'][key]
            return

        mbids = [x for x in mbids if x]  # drop None and "" from list of mbids if any

        for mbid in mbids:
            if not is_valid_uuid(mbid):   # if the mbid is invalid raise an error
                raise ListenValidationError("%s MBID format invalid." % (key,), listen)

        listen['track_metadata']['additional_info'][key] = mbids  # set the filtered in the listen payload


def validate_listened_at(listen):
    """ Raises an error if the listened_at timestamp is invalid. The timestamp is invalid
    if it is lower than the minimum acceptable timestamp or if its in future beyond
    tolerable skew.

    Args:
        listen: the listen to be validated
    """
    if "listened_at" not in listen:
        raise ListenValidationError("JSON document must contain the key listened_at at the top level.", listen)

    try:
        listen["listened_at"] = int(listen["listened_at"])
    except (ValueError, TypeError):
        raise ListenValidationError("JSON document must contain an int value for listened_at.", listen)

    # raise error if timestamp is too high
    # in order to make up for possible clock skew, we allow
    # timestamps to be one hour ahead of server time
    if listen["listened_at"] >= int(time.time()) + API_LISTENED_AT_ALLOWED_SKEW:
        raise ListenValidationError("Value for key listened_at is too high.", listen)

    if listen["listened_at"] < LISTEN_MINIMUM_TS:
        raise ListenValidationError("Value for key listened_at is too low. listened_at timestamp "
                                    "should be greater than 1033410600 (2002-10-01 00:00:00 UTC).", listen)


def publish_data_to_queue(data, exchange):
    """ Publish specified data to the specified queue.

    Args:
        data: the data to be published
        exchange: the name of the exchange
    """
    try:
        with rabbitmq_connection.rabbitmq.acquire(block=True, timeout=60) as producer:
            producer.publish(
                exchange=exchange,
                routing_key='',
                body=orjson.dumps(data),
                delivery_mode=PERSISTENT_DELIVERY_MODE,
                retry=True,
                retry_policy={"max_retries": 5},
                declare=[exchange]
            )
    except Exception:
        current_app.logger.error("Cannot publish to rabbitmq channel:", exc_info=True)
        raise APIServiceUnavailable("Cannot submit listens to queue, please try again later.")


def get_non_negative_param(param, default=None):
    """ Gets the value of a request parameter, validating that it is non-negative

    Args:
        param (str): the parameter to get
        default: the value to return if the parameter doesn't exist in the request
    """
    value = request.args.get(param, default)
    if value is not None:
        try:
            value = int(value)
        except ValueError:
            raise APIBadRequest("'{}' should be a non-negative integer".format(param))

        if value < 0:
            raise APIBadRequest("'{}' should be a non-negative integer".format(param))
    return value


def parse_param_list(params: str) -> list:
    """ Splits a string of comma separated values into a list """
    param_list = []
    for param in params.split(","):
        param = param.strip()
        if not param:
            continue
        param_list.append(param)

    return param_list


def _parse_int_arg(name, default=None):
    value = request.args.get(name)
    if value:
        try:
            return int(value)
        except ValueError:
            raise APIBadRequest("Invalid %s argument: %s" % (name, value))
    else:
        return default


def _parse_bool_arg(name, default=None):
    value = request.args.get(name)
    if value:
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        else:
            raise APIBadRequest("Invalid %s argument: %s" % (name, value))
    else:
        return default


def _validate_get_endpoint_params() -> Tuple[int, int, int]:
    """ Validates parameters for listen GET endpoints like /username/listens and /username/feed/events

    Returns a tuple of integers: (min_ts, max_ts, count)
    """
    max_ts = _parse_int_arg("max_ts")
    min_ts = _parse_int_arg("min_ts")

    if max_ts and min_ts:
        if max_ts < min_ts:
            log_raise_400("max_ts should be greater than min_ts")

    # Validate requested listen count is positive
    count = min(_parse_int_arg(
        "count", DEFAULT_ITEMS_PER_GET), MAX_ITEMS_PER_GET)
    if count < 0:
        log_raise_400("Number of items requested should be positive")

    return min_ts, max_ts, count


def validate_auth_header(*, optional: bool = False, fetch_email: bool = False, scopes: list[str] = None):
    """ Examine the current request headers for an Authorization: Token <uuid>
        header that identifies a LB user and then load the corresponding user
        object from the database and return it, if successful. Otherwise raise
        APIUnauthorized() exception.

    Args:
        optional: If the optional flag is given, do not raise an exception
            if the Authorization header is not set.
        fetch_email: if True, include email in the returned dict
        scopes: the scopes the access token is required to have access to
    """
    auth_token = request.headers.get("Authorization")
    if not auth_token:
        if optional:
            return None
        raise APIUnauthorized("You need to provide an Authorization header.")

    try:
        auth_token = auth_token.split(" ")[1]
    except IndexError:
        raise APIUnauthorized("Provided Authorization header is invalid.")

    if auth_token.startswith("meba_"):
        try:
            response = requests.post(
                current_app.config["OAUTH_INTROSPECTION_URL"],
                data={
                    "client_id": current_app.config["OAUTH_CLIENT_ID"],
                    "client_secret": current_app.config["OAUTH_CLIENT_SECRET"],
                    "token": auth_token,
                    "token_type_hint": "access_token",
                }
            )
            token = response.json()
        except requests.exceptions.RequestException:
            logger.error("Error while trying to introspect token:", exc_info=True)
            raise APIServiceUnavailable("Something is wrong. Please try again later.")

        if not token["active"] or datetime.fromtimestamp(token["expires_at"]) < datetime.now():
            raise APIUnauthorized("Invalid access token.")

        if scopes:
            token_scopes = token["scope"]
            for scope in scopes:
                if scope not in token_scopes:
                    raise APIUnauthorized("Insufficient scope.")

        user = db_user.get_by_mb_id(db_conn, token["sub"], fetch_email=fetch_email)
    else:
        user = db_user.get_by_token(db_conn, auth_token, fetch_email=fetch_email)

    if user is None:
        raise APIUnauthorized("Invalid authorization token.")

    return user


def _allow_metabrainz_domains(tag, name, value):
    """A bleach attribute cleaner for <a> tags that only allows hrefs to point
    to metabrainz-controlled domains"""

    metabrainz_domains = ["acousticbrainz.org", "critiquebrainz.org", "listenbrainz.org",
                          "metabrainz.org", "musicbrainz.org"]

    if name == "rel":
        return True
    elif name == "href":
        p = urlparse(value)
        return (not p.netloc) or p.netloc in metabrainz_domains
    else:
        return False


def _filter_description_html(description):
    ok_tags = [u"a", u"strong", u"b", u"em", u"i", u"u", u"ul", u"li", u"p", u"br"]
    return bleach.clean(description, tags=ok_tags, attributes={"a": _allow_metabrainz_domains}, strip=True)
