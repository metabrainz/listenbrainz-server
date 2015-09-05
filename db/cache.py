"""
This module serves as an interface to memcached instance.

Module needs to be initialized before use. See init() function.

It basically serves as a wrapper for python-memcached package with additional
functionality and tweaks specific to our needs.

There's also support for namespacing, which simplifies management of different
versions of data saved in the cache. You can invalidate whole namespace using
invalidate_namespace() function. See its description for more info.

Package python-memcached is available at https://pypi.python.org/pypi/python-memcached/.
More information about memcached can be found at http://memcached.org/.
"""
import memcache
import hashlib
import six

_mc = None
_glob_namespace = "AB"


def init(servers, namespace="AB", debug=0):
    """Initializes memcached client. Needs to be called before use.

    Args:
        server: List of strings with memcached server addresses (host:port).
        namespace: Optional global namespace that will be prepended to all keys.
        debug: Whether to display error messages when a server can't be contacted.
    """
    global _mc, _glob_namespace
    _mc = memcache.Client(servers, debug=debug)
    # TODO(roman): Check length of the namespace (should fit with hash appended):
    _glob_namespace = namespace + ":"


def set(key, val, time=0, namespace=None):
    """Set a key to a given value.

    Args:
        key: Key of the item.
        value: Item's value.
        time: The time after which this value should expire, either as a delta
            number of seconds, or an absolute unix time-since-the-epoch value.
            If set to 0, value will be stored "forever".
        namespace: Optional namespace in which key needs to be defined.

    Returns:
        True if stored successfully, False otherwise.
    """
    if _mc is None: return
    not_stored_count = set_multi({key: val}, time, namespace)
    return len(not_stored_count) == 0


def get(key, namespace=None):
    """Retrieve an item.

    Args:
        key: Key of the item that needs to be retrieved.
        namespace: Optional namespace in which key was defined.

    Returns:
        Stored value or None if it's not found.
    """
    if _mc is None: return
    key = _prep_key(key, namespace)
    result = _mc.get_multi([key], _glob_namespace)
    return result[key] if key in result else None


def delete(key, namespace=None):
    """Delete an item.

    Args:
        key: Key of the item that needs to be deleted.
        namespace: Optional namespace in which key was defined.

    Returns:
          True if deleted successfully, False otherwise.
    """
    if _mc is None: return
    return delete_multi([key], namespace) == 1


def set_multi(mapping, time=0, namespace=None):
    """Set multiple keys doing just one query.

    Args:
        mapping: A dict of key/value pairs to set.

    Returns:
        List of keys which failed to be stored (memcache out of memory, etc.).
    """
    if _mc is None: return
    return _mc.set_multi(_prep_dict(mapping, namespace), time, _glob_namespace)


def get_multi(keys, namespace=None):
    """Retrieve multiple keys doing just one query.

    Args:
        keys: Array of keys that need to be retrieved.

    Returns:
        A dictionary of key/value pairs that were available. If key_prefix was
        provided, the keys in the returned dictionary will not have it present.
    """
    if _mc is None: return {}
    return _mc.get_multi(_prep_list(keys, namespace), _glob_namespace)


def delete_multi(keys, namespace=None):
    if _mc is None: return
    return _mc.delete_multi(_prep_list(keys, namespace), key_prefix=_glob_namespace)


def gen_key(key, *attributes):
    """Helper function that generates a key with attached attributes.

    Args:
        key: Original key.
        attributes: Attributes that will be appended a key.

    Returns:
        Key that can be used with cache.
    """
    if not isinstance(key, six.string_types):
        key = str(key)
    key = key.encode('ascii', errors='xmlcharrefreplace')

    for attr in attributes:
        if not isinstance(attr, six.string_types):
            attr = str(attr)
        key += '_' + attr.encode('ascii', errors='xmlcharrefreplace')

    key = key.replace(' ', '_')  # spaces are not allowed

    return key


def invalidate_namespace(namespace):
    """Invalidates specified namespace.

    Invalidation is done by incrementing version of the namespace

    Args:
        namespace: Namespace that needs to be invalidated.
    """
    if _mc is None: return
    version_key = _glob_namespace + namespace
    if _mc.incr(version_key) is None:  # namespace isn't initialized
        _mc.set(version_key, 1)  # initializing the namespace


def flush_all():
    if _mc is None: return
    _mc.flush_all()


def _get_namespace_version(namespace):
    if _mc is None: return
    version_key = _glob_namespace + namespace
    version = _mc.get(version_key)
    if version is None:  # namespace isn't initialized
        version = 1
        _mc.set(version_key, version)  # initializing the namespace
    return version


def _prep_key(key, namespace=None):
    """Prepares a key for use with memcached."""
    if _mc is None: return
    if namespace:
        key = "%s:%s:%s" % (namespace, _get_namespace_version(namespace), key)
    if not isinstance(key, six.string_types):
        key = str(key)
    key = six.b(hashlib.sha1(six.b(key)).hexdigest())
    _mc.check_key(key)
    return key


def _prep_list(l, namespace=None):
    """Wrapper for _prep_key function that works with lists."""
    return [_prep_key(k, namespace) for k in l]


def _prep_dict(dictionary, namespace=None):
    """Wrapper for _prep_key function that works with dictionaries."""
    for key in dictionary.keys():
        dictionary[_prep_key(key, namespace)] = dictionary.pop(key)
    return dictionary
