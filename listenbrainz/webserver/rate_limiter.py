# The original version of this code was written by Armin Ronacher:
#
# This snippet by Armin Ronacher can be used freely for anything you like. Consider it public domain.
#
# http://flask.pocoo.org/snippets/70/
#
import time
from functools import update_wrapper
from flask import request, g
from listenbrainz.webserver import redis_connection
import listenbrainz.db.user as db_user
from listenbrainz.redis_keys import RATELIMIT_PER_TOKEN_KEY, RATELIMIT_PER_IP_KEY, RATELIMIT_WINDOW_KEY

# Defaults
RATELIMIT_PER_TOKEN_DEFAULT = 50
RATELIMIT_PER_IP_DEFAULT = 30
RATELIMIT_WINDOW_DEFAULT = 10

# g key for the timeout when limits must be refreshed from redis
RATELIMIT_REFRESH = 60 # in seconds
RATELIMIT_TIMEOUT = "rate_limits_timeout"

# Add rate limit headers to responses
def inject_x_rate_headers(response):
    limit = get_view_rate_limit()
    if limit:
        h = response.headers
        h.add('Access-Control-Expose-Headers', 'X-RateLimit-Remaining,X-RateLimit-Limit,X-RateLimit-Reset,X-RateLimit-Reset-In')
        h.add('X-RateLimit-Remaining', str(limit.remaining))
        h.add('X-RateLimit-Limit', str(limit.limit))
        h.add('X-RateLimit-Reset', str(limit.reset))
        h.add('X-RateLimit-Reset-In', str(limit.seconds_before_reset))
    return response

class RateLimit(object):

    # From the docs:
    # We also give the key extra expiration_window seconds time to expire in redis so that badly
    # synchronized clocks between the workers and the redis server do not cause problems.
    expiration_window = 10

    def __init__(self, key_prefix, limit, per):
        current_time = int(time.time())
        self.reset = (current_time // per) * per + per
        self.seconds_before_reset = self.reset - current_time
        self.key = key_prefix + str(self.reset)
        self.limit = limit
        self.per = per
        p = redis_connection._redis.redis.pipeline()
        p.incr(self.key)
        p.expireat(self.key, self.reset + self.expiration_window)
        self.current = p.execute()[0]

    remaining = property(lambda x: max(x.limit - x.current, 0))
    over_limit = property(lambda x: x.current > x.limit)

def get_view_rate_limit():
    return getattr(g, '_view_rate_limit', None)

def on_over_limit(limit):
    return 'You have exceeded your rate limit. See the X-RateLimit-* response headers for more ' \
           'information on your current rate limit.\n', 429

def set_rate_limits(per_ip, per_token, window):
    redis_connection._redis.redis.put(RATELIMIT_PER_TOKEN_KEY, per_token)
    redis_connection._redis.redis.put(RATELIMIT_PER_IP_KEY, per_ip)
    redis_connection._redis.redis.put(RATELIMIT_WINDOW_KEY, window)

def check_limit_freshness():
    limits_timeout = getattr(g, '_' + RATELIMIT_TIMEOUT, 0)
    if time.time() <= limits_timeout:
        return

    value = int(redis_connection._redis.redis.get(RATELIMIT_PER_TOKEN_KEY) or '0')
    if not value:
        redis_connection._redis.redis.set(RATELIMIT_PER_TOKEN_KEY, RATELIMIT_PER_TOKEN_DEFAULT)
        value = RATELIMIT_PER_TOKEN_DEFAULT
    setattr(g, '_' + RATELIMIT_PER_TOKEN_KEY, value)

    value = int(redis_connection._redis.redis.get(RATELIMIT_PER_IP_KEY) or '0')
    if not value:
        redis_connection._redis.redis.set(RATELIMIT_PER_IP_KEY, RATELIMIT_PER_IP_DEFAULT)
        value = RATELIMIT_PER_IP_DEFAULT
    setattr(g, '_' + RATELIMIT_PER_IP_KEY, value)

    value = int(redis_connection._redis.redis.get(RATELIMIT_WINDOW_KEY) or '0')
    if not value:
        redis_connection._redis.redis.set(RATELIMIT_WINDOW_KEY, RATELIMIT_WINDOW_DEFAULT)
        value = RATELIMIT_WINDOW_DEFAULT
    setattr(g, '_' + RATELIMIT_WINDOW_KEY, value)

    setattr(g, '_' + RATELIMIT_TIMEOUT, int(time.time()) + RATELIMIT_REFRESH)

def get_per_ip_limits():
    check_limit_freshness()
    return {
            'limit':   getattr(g, '_' + RATELIMIT_PER_IP_KEY),
            'window' : getattr(g, '_' + RATELIMIT_WINDOW_KEY),
           }

def get_per_token_limits():
    check_limit_freshness()
    return {
            'limit':   getattr(g, '_' + RATELIMIT_PER_TOKEN_KEY),
            'window' : getattr(g, '_' + RATELIMIT_WINDOW_KEY),
           }

def get_rate_limit_data(request):
    '''Fetch key for the given request. If an Authorization header is provided,
       the caller will get a better and personalized rate limit. If no header is provided,
       the caller will be rate limited by IP, which gets an overall lower rate limit.
       This should encourage callers to always provide the Authorization token
    '''

    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth_token = auth_header[6:]
        user = db_user.get_by_token(auth_token)
        if user:
            values = get_per_token_limits()
            values['key'] = auth_token
            return values

    # no valid auth token provided. Look for a remote addr header provided a the proxy
    # or if that isn't available use the IP address from the header
    ip = request.headers.get('X-LB-Remote-Addr')
    if not ip:
        ip = request.remote_addr

    values = get_per_ip_limits()
    values['key'] = ip
    return values


def ratelimit():
    def decorator(f):
        def rate_limited(*args, **kwargs):
            data = get_rate_limit_data(request)
            key = 'rate-limit/%s/' % data['key']
            rlimit = RateLimit(key, data['limit'], data['window'])
            g._view_rate_limit = rlimit
            if rlimit.over_limit:
                return on_over_limit(rlimit)
            return f(*args, **kwargs)
        return update_wrapper(rate_limited, f)
    return decorator
