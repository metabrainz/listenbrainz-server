import string
import random


def generate_string(length):
    """Generates random string with a specified length."""
    return ''.join([random.SystemRandom().choice(
        string.ascii_letters + string.digits
    ) for _ in range(length)])


def sizeof_readable(num, suffix='B'):
    """ Converts the size in human readable format """

    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yb', suffix)


def reformat_date(value, fmt="%b %d, %Y"):
    return value.strftime(fmt)


def reformat_datetime(value, fmt="%b %d, %Y, %H:%M %Z"):
    return value.strftime(fmt)

def init_cache(app):
    from brainzutils import cache
    import logging
    try:
        cache.init(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            namespace=app.config['REDIS_NAMESPACE'],
        )
    except KeyError as e:
        logging.error("Redis is not defined in config file. Error: {}".format(e))
        raise
