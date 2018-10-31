import listenbrainz.webserver.rabbitmq_connection as rabbitmq_connection
import listenbrainz.webserver.redis_connection as redis_connection
import pika
import pika.exceptions
import sys
import time
import ujson
import uuid

from flask import current_app
from listenbrainz.listen import Listen
from listenbrainz.webserver import API_LISTENED_AT_ALLOWED_SKEW
from listenbrainz.webserver.external import messybrainz
from werkzeug.exceptions import InternalServerError, ServiceUnavailable, BadRequest

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
        augmented_listens = _get_augmented_listens(payload, user, listen_type)
        _send_listens_to_queue(listen_type, augmented_listens)
    except (InternalServerError, ServiceUnavailable) as e:
        raise
    except Exception as e:
        print(e)
    return augmented_listens


def _send_listens_to_queue(listen_type, listens):
    submit = []
    for listen in listens:
        if listen_type == LISTEN_TYPE_PLAYING_NOW:
            try:
                expire_time = listen["track_metadata"]["additional_info"].get("duration",
                                    current_app.config['PLAYING_NOW_MAX_DURATION'])
                redis_connection._redis.redis.setex(
                    'playing_now:{}'.format(listen['user_id']),
                    ujson.dumps(listen).encode('utf-8'),
                    expire_time
                )
            except Exception as e:
                current_app.logger.error("Redis rpush playing_now write error: " + str(e))
                raise ServiceUnavailable("Cannot record playing_now at this time.")
        else:
            submit.append(listen)

    if submit:
        # check if rabbitmq connection exists or not
        # and if not then try to connect
        try:
            rabbitmq_connection.init_rabbitmq_connection(current_app)
        except ConnectionError as e:
            current_app.logger.error('Cannot connect to RabbitMQ: %s' % str(e))
            raise ServiceUnavailable('Cannot submit listens to queue, please try again later.')

        publish_data_to_queue(
            data=submit,
            exchange=current_app.config['INCOMING_EXCHANGE'],
            queue=current_app.config['INCOMING_QUEUE'],
            error_msg='Cannot submit listens to queue, please try again later.',
        )


def validate_listen(listen, listen_type):
    """Make sure that required keys are present, filled out and not too large."""

    if listen_type in (LISTEN_TYPE_SINGLE, LISTEN_TYPE_IMPORT):
        if 'listened_at' not in listen:
            log_raise_400("JSON document must contain the key listened_at at the top level.", listen)

        try:
            listen['listened_at'] = int(listen['listened_at'])
        except ValueError:
            log_raise_400("JSON document must contain an int value for listened_at.", listen)

        if 'listened_at' in listen and 'track_metadata' in listen and len(listen) > 2:
            log_raise_400("JSON document may only contain listened_at and "
                           "track_metadata top level keys", listen)

        # if timestamp is too high, raise BadRequest
        # in order to make up for possible clock skew, we allow
        # timestamps to be one hour ahead of server time
        if not is_valid_timestamp(listen['listened_at']):
            log_raise_400("Value for key listened_at is too high.", listen)

    elif listen_type == LISTEN_TYPE_PLAYING_NOW:
        if 'listened_at' in listen:
            log_raise_400("JSON document must not contain listened_at while submitting "
                           "playing_now.", listen)

        if 'track_metadata' in listen and len(listen) > 1:
            log_raise_400("JSON document may only contain track_metadata as top level "
                           "key when submitting now_playing.", listen)

    # Basic metadata
    try:
        if not listen['track_metadata']['track_name']:
            log_raise_400("JSON document does not contain required "
                           "track_metadata.track_name.", listen)
        if not listen['track_metadata']['artist_name']:
            log_raise_400("JSON document does not contain required "
                           "track_metadata.artist_name.", listen)
        if not isinstance(listen['track_metadata']['artist_name'], str):
            log_raise_400("artist_name must be a single string.", listen)
    except KeyError:
        log_raise_400("JSON document does not contain a valid metadata.track_name "
                       "and/or track_metadata.artist_name.", listen)

    if 'additional_info' in listen['track_metadata']:
        # Tags
        if 'tags' in listen['track_metadata']['additional_info']:
            tags = listen['track_metadata']['additional_info']['tags']
            if len(tags) > MAX_TAGS_PER_LISTEN:
                log_raise_400("JSON document may not contain more than %d items in "
                               "track_metadata.additional_info.tags." % MAX_TAGS_PER_LISTEN, listen)
            for tag in tags:
                if len(tag) > MAX_TAG_SIZE:
                    log_raise_400("JSON document may not contain track_metadata.additional_info.tags "
                                   "longer than %d characters." % MAX_TAG_SIZE, listen)
        # MBIDs
        single_mbid_keys = ['release_mbid', 'recording_mbid', 'release_group_mbid', 'track_mbid']
        for key in single_mbid_keys:
            verify_mbid_validity(listen, key, multi = False)
        multiple_mbid_keys = ['artist_mbids', 'work_mbids']
        for key in multiple_mbid_keys:
            verify_mbid_validity(listen, key, multi = True)


# lifted from AcousticBrainz
def is_valid_uuid(u):
    try:
        u = uuid.UUID(u)
        return True
    except ValueError:
        return False


def _get_augmented_listens(payload, user, listen_type):
    """ Converts the payload to augmented list after lookup
        in the MessyBrainz database
    """

    augmented_listens = []
    msb_listens = []
    for l in payload:
        listen = l.copy()   # Create a local object to prevent the mutation of the passed object
        listen['user_id'] = user['id']
        listen['user_name'] = user['musicbrainz_id']

        msb_listens.append(listen)
        if len(msb_listens) >= MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP:
            augmented_listens.extend(_messybrainz_lookup(msb_listens))
            msb_listens = []

    if msb_listens:
        augmented_listens.extend(_messybrainz_lookup(msb_listens))
    return augmented_listens


def _messybrainz_lookup(listens):

    msb_listens = []
    for listen in listens:
        messy_dict = {
            'artist': listen['track_metadata']['artist_name'],
            'title': listen['track_metadata']['track_name'],
        }
        if 'release_name' in listen['track_metadata']:
            messy_dict['release'] = listen['track_metadata']['release_name']

        if 'additional_info' in listen['track_metadata']:
            ai = listen['track_metadata']['additional_info']
            if 'artist_mbids' in ai and isinstance(ai['artist_mbids'], list):
                messy_dict['artist_mbids'] = ai['artist_mbids']
            if 'release_mbid' in ai:
                messy_dict['release_mbid'] = ai['release_mbid']
            if 'recording_mbid' in ai:
                messy_dict['recording_mbid'] = ai['recording_mbid']
            if 'track_number' in ai:
                messy_dict['track_number'] = ai['track_number']
            if 'spotify_id' in ai:
                messy_dict['spotify_id'] = ai['spotify_id']
        msb_listens.append(messy_dict)

    try:
        msb_responses = messybrainz.submit_listens(msb_listens)
    except messybrainz.exceptions.BadDataException as e:
        log_raise_400(str(e))
    except messybrainz.exceptions.NoDataFoundException:
        return []
    except messybrainz.exceptions.ErrorAddingException as e:
        raise ServiceUnavailable(str(e))

    augmented_listens = []
    for listen, messybrainz_resp in zip(listens, msb_responses['payload']):
        messybrainz_resp = messybrainz_resp['ids']

        if 'additional_info' not in listen['track_metadata']:
            listen['track_metadata']['additional_info'] = {}

        try:
            listen['recording_msid'] = messybrainz_resp['recording_msid']
            listen['track_metadata']['additional_info']['artist_msid'] = messybrainz_resp['artist_msid']
        except KeyError:
            current_app.logger.error("MessyBrainz did not return a proper set of ids")
            raise InternalServerError

        try:
            listen['track_metadata']['additional_info']['release_msid'] = messybrainz_resp['release_msid']
        except KeyError:
            pass

        artist_mbids = messybrainz_resp.get('artist_mbids', [])
        release_mbid = messybrainz_resp.get('release_mbid', None)
        recording_mbid = messybrainz_resp.get('recording_mbid', None)

        if 'artist_mbids'   not in listen['track_metadata']['additional_info'] and \
           'release_mbid'   not in listen['track_metadata']['additional_info'] and \
           'recording_mbid' not in listen['track_metadata']['additional_info']:

            if len(artist_mbids) > 0 and release_mbid and recording_mbid:
                listen['track_metadata']['additional_info']['artist_mbids'] = artist_mbids
                listen['track_metadata']['additional_info']['release_mbid'] = release_mbid
                listen['track_metadata']['additional_info']['recording_mbid'] = recording_mbid

        augmented_listens.append(listen)
    return augmented_listens


def log_raise_400(msg, data=""):
    """ Helper function for logging issues with request data and showing error page.
        Logs the message and data, raises BadRequest exception which shows 400 Bad
        Request to the user.
    """

    if isinstance(data, dict):
        data = ujson.dumps(data)

    current_app.logger.debug("BadRequest: %s\nJSON: %s" % (msg, data))
    raise BadRequest(msg)


def verify_mbid_validity(listen, key, multi):
    """ Verify that mbid(s) present in listen with key `key` is valid.

        Args:
            listen: listen data
            key: the key whose mbids is to be validated
            multi: boolean value signifying if the key contains multiple mbids
    """
    if not multi:
        items = listen['track_metadata']['additional_info'].get(key)
        items = [items] if items else []
    else:
        items = listen['track_metadata']['additional_info'].get(key, [])
    for item in items:
        if not is_valid_uuid(item):
            log_raise_400("%s MBID format invalid." % (key, ), listen)


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
        current_app.logger.error("Connection to rabbitmq closed while trying to publish: %s" % str(e))
        raise ServiceUnavailable(error_msg)
    except PikaPoolOverflow:
        current_app.logger.error("Cannot acquire pika channel. Increase number of available channels.")
        raise ServiceUnavailable(error_msg)
    except PikaPoolTimeout as e:
        current_app.logger.error("Cannot publish to rabbitmq channel -- timeout: %s" % str(e))
        raise ServiceUnavailable(error_msg)
    except Exception as e:
        current_app.logger.error("Cannot publish to rabbitmq channel: %s / %s" % (type(e).__name__, str(e)))
        raise ServiceUnavailable(error_msg)
