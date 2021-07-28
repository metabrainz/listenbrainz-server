from typing import Dict
from urllib.parse import urlparse

import bleach

import listenbrainz.webserver.rabbitmq_connection as rabbitmq_connection
import listenbrainz.webserver.redis_connection as redis_connection
import listenbrainz.db.user as db_user
import pika
import pika.exceptions
import time
import ujson
import uuid

from flask import current_app, request

from listenbrainz.webserver import API_LISTENED_AT_ALLOWED_SKEW
from listenbrainz.webserver.errors import APIInternalServerError, APIServiceUnavailable, APIBadRequest, APIUnauthorized
#: Maximum overall listen size in bytes, to prevent egregious spamming.
MAX_LISTEN_SIZE = 10240

#: The maximum number of tags per listen.
MAX_TAGS_PER_LISTEN = 50

#: The maximum length of a tag
MAX_TAG_SIZE = 64

#: The maximum number of listens returned in a single GET request.
MAX_ITEMS_PER_GET = 100

#: The default number of listens returned in a single GET request.
DEFAULT_ITEMS_PER_GET = 25

MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP = 10


# Define the values for types of listens
LISTEN_TYPE_SINGLE = 1
LISTEN_TYPE_IMPORT = 2
LISTEN_TYPE_PLAYING_NOW = 3


def insert_payload(payload, user, listen_type=LISTEN_TYPE_IMPORT):
    """ Convert the payload into augmented listens then submit them.
        Returns: augmented_listens
    """
    try:
        augmented_listens = _get_augmented_listens(payload, user)
        _send_listens_to_queue(listen_type, augmented_listens)
    except (APIInternalServerError, APIServiceUnavailable):
        raise
    except Exception as e:
        current_app.logger.error("Error while inserting payload: %s", str(e), exc_info=True)
        raise APIInternalServerError("Something went wrong. Please try again.")
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
        # check if rabbitmq connection exists or not
        # and if not then try to connect
        try:
            rabbitmq_connection.init_rabbitmq_connection(current_app)
        except ConnectionError as e:
            current_app.logger.error('Cannot connect to RabbitMQ: %s' % str(e))
            raise APIServiceUnavailable('Cannot submit listens to queue, please try again later.')

        if listen_type == LISTEN_TYPE_PLAYING_NOW:
           exchange = current_app.config['PLAYING_NOW_EXCHANGE']
           queue = current_app.config['PLAYING_NOW_QUEUE']
        else:
            exchange = current_app.config['INCOMING_EXCHANGE']
            queue = current_app.config['INCOMING_QUEUE']

        publish_data_to_queue(
            data=submit,
            exchange=exchange,
            queue=queue,
            error_msg='Cannot submit listens to queue, please try again later.',
        )


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
        raise APIBadRequest("Listen is empty and cannot be validated.")

    if listen_type in (LISTEN_TYPE_SINGLE, LISTEN_TYPE_IMPORT):
        if 'listened_at' not in listen:
            raise APIBadRequest("JSON document must contain the key listened_at at the top level.", listen)

        try:
            listen['listened_at'] = int(listen['listened_at'])
        except ValueError:
            raise APIBadRequest("JSON document must contain an int value for listened_at.", listen)

        if 'listened_at' in listen and 'track_metadata' in listen and len(listen) > 2:
            raise APIBadRequest("JSON document may only contain listened_at and "
                                "track_metadata top level keys", listen)

        # if timestamp is too high, raise BadRequest
        # in order to make up for possible clock skew, we allow
        # timestamps to be one hour ahead of server time
        if not is_valid_timestamp(listen['listened_at']):
            raise APIBadRequest("Value for key listened_at is too high.", listen)

    elif listen_type == LISTEN_TYPE_PLAYING_NOW:
        if 'listened_at' in listen:
            raise APIBadRequest("JSON document must not contain listened_at while submitting "
                                "playing_now.", listen)

        if 'track_metadata' in listen and len(listen) > 1:
            raise APIBadRequest("JSON document may only contain track_metadata as top level "
                                "key when submitting playing_now.", listen)

    # Basic metadata
    if 'track_name' in listen['track_metadata']:
        if not isinstance(listen['track_metadata']['track_name'], str):
            raise APIBadRequest("track_metadata.track_name must be a single string.", listen)

        listen['track_metadata']['track_name'] = listen['track_metadata']['track_name'].strip()
        if len(listen['track_metadata']['track_name']) == 0:
            raise APIBadRequest("required field track_metadata.track_name is empty.", listen)
    else:
        raise APIBadRequest("JSON document does not contain required track_metadata.track_name.", listen)


    if 'artist_name' in listen['track_metadata']:
        if not isinstance(listen['track_metadata']['artist_name'], str):
            raise APIBadRequest("track_metadata.artist_name must be a single string.", listen)

        listen['track_metadata']['artist_name'] = listen['track_metadata']['artist_name'].strip()
        if len(listen['track_metadata']['artist_name']) == 0:
            raise APIBadRequest("required field track_metadata.artist_name is empty.", listen)
    else:
        raise APIBadRequest("JSON document does not contain required track_metadata.artist_name.", listen)


    if 'additional_info' in listen['track_metadata']:
        # Tags
        if 'tags' in listen['track_metadata']['additional_info']:
            tags = listen['track_metadata']['additional_info']['tags']
            if len(tags) > MAX_TAGS_PER_LISTEN:
                raise APIBadRequest("JSON document may not contain more than %d items in "
                                    "track_metadata.additional_info.tags." % MAX_TAGS_PER_LISTEN, listen)
            for tag in tags:
                if len(tag) > MAX_TAG_SIZE:
                    raise APIBadRequest("JSON document may not contain track_metadata.additional_info.tags "
                                        "longer than %d characters." % MAX_TAG_SIZE, listen)
        # MBIDs, both of the mbid validation methods mutate the listen payload if needed.
        single_mbid_keys = ['release_mbid', 'recording_mbid', 'release_group_mbid', 'track_mbid']
        for key in single_mbid_keys:
            validate_single_mbid_field(listen, key)
        multiple_mbid_keys = ['artist_mbids', 'work_mbids']
        for key in multiple_mbid_keys:
            validate_multiple_mbids_field(listen, key)

    # If unicode null is present in the listen, postgres will raise an
    # error while trying to insert it. hence, reject such listens.
    check_for_unicode_null_recursively(listen)

    return listen


# lifted from AcousticBrainz
def is_valid_uuid(u):
    try:
        u = uuid.UUID(u)
        return True
    except (AttributeError, ValueError):
        return False


def _get_augmented_listens(payload, user):
    """ Converts the payload to augmented list after adding user_id and user_name attributes """
    for listen in payload:
        listen['user_id'] = user['id']
        listen['user_name'] = user['musicbrainz_id']
    return payload


def log_raise_400(msg, data=""):
    """ Helper function for logging issues with request data and showing error page.
        Logs the message and data, raises BadRequest exception which shows 400 Bad
        Request to the user.
    """

    if isinstance(data, dict):
        data = ujson.dumps(data)

    current_app.logger.debug("BadRequest: %s\nJSON: %s" % (msg, data))
    raise APIBadRequest(msg)


def validate_single_mbid_field(listen, key):
    """ Verify that mbid if present in the listen with given key is valid.
    An APIBadRequest error is raised for invalid values of mbids.

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
            log_raise_400("%s MBID format invalid." % (key, ), listen)


def validate_multiple_mbids_field(listen, key):
    """ Verify that all the mbids in the list if present in the listen with
    given key are valid. An APIBadRequest error is raised for if any mbid is
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
                log_raise_400("%s MBID format invalid." % (key,), listen)

        listen['track_metadata']['additional_info'][key] = mbids  # set the filtered in the listen payload

def is_valid_timestamp(ts):
    """ Returns True if the timestamp passed is in the API's
    allowed range of timestamps, False otherwise

    Args:
        ts (int): the timestamp to be checked for validity

    Returns:
        bool: True if timestamp is valid, False otherwise
    """
    return ts <= int(time.time()) + API_LISTENED_AT_ALLOWED_SKEW


def publish_data_to_queue(data, exchange, queue, error_msg):
    """ Publish specified data to the specified queue.

    Args:
        data: the data to be published
        exchange (str): the name of the exchange
        queue (str): the name of the queue
        error_msg (str): the error message to be returned in case of an error
    """
    try:
        with rabbitmq_connection._rabbitmq.get() as connection:
            channel = connection.channel
            channel.exchange_declare(exchange=exchange, exchange_type='fanout')
            channel.queue_declare(queue, durable=True)
            channel.basic_publish(
                exchange=exchange,
                routing_key='',
                body=ujson.dumps(data),
                properties=pika.BasicProperties(delivery_mode=2, ),
            )
    except pika.exceptions.ConnectionClosed as e:
        current_app.logger.error("Connection to rabbitmq closed while trying to publish: %s" % str(e), exc_info=True)
        raise APIServiceUnavailable(error_msg)
    except Exception as e:
        current_app.logger.error("Cannot publish to rabbitmq channel: %s / %s" % (type(e).__name__, str(e)), exc_info=True)
        raise APIServiceUnavailable(error_msg)


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


def validate_auth_header(*, optional: bool = False, fetch_email: bool = False):
    """ Examine the current request headers for an Authorization: Token <uuid>
        header that identifies a LB user and then load the corresponding user
        object from the database and return it, if succesful. Otherwise raise
        APIUnauthorized() exception.

    Args:
        optional: If the optional flag is given, do not raise an exception
            if the Authorization header is not set.
        fetch_email: if True, include email in the returned dict
    """

    auth_token = request.headers.get('Authorization')
    if not auth_token:
        if optional:
            return None
        raise APIUnauthorized("You need to provide an Authorization header.")
    try:
        auth_token = auth_token.split(" ")[1]
    except IndexError:
        raise APIUnauthorized("Provided Authorization header is invalid.")

    user = db_user.get_by_token(auth_token, fetch_email=fetch_email)
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
