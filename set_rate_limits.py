#!/usr/bin/env python

import sys
from redis import Redis
#from webserver.rate_limiter import RATELIMIT_PER_TOKEN_KEY
#from webserver.rate_limiter import RATELIMIT_PER_IP_KEY
#from webserver.rate_limiter import RATELIMIT_WINDOW_KEY
import config

# TODO: Do not duplicate these. Import from webserver when doing the source tree re-org
RATELIMIT_PER_TOKEN_KEY = "rate_limit_per_token_limit"
RATELIMIT_PER_IP_KEY = "rate_limit_per_ip_limit"
RATELIMIT_WINDOW_KEY = "rate_limit_window"

# Yes, I could use getoptgetargparsewtfbbw, but then I would spend 20 mimnutes re-learning the stupid syntax.
# Or, I could just do it myself in the space of seconds.
# Also, I tried to integrate this script with manage.py, but then I ended up wasting an hour trying
# to figure out how to do this. So, we have this script. If you want to see it part of manage.py, you'll
# have to do it.

r = Redis(config.REDIS_HOST)
if len(sys.argv) < 4:
    print "Usage: %s <per ip limit> <per token limit> <window in s>" % (sys.argv[0])
    print "Current values:"
    print "      Requests per ip: ", r.get(RATELIMIT_PER_IP_KEY)
    print "   Requests per token: ", r.get(RATELIMIT_PER_TOKEN_KEY)
    print "          window size: ", r.get(RATELIMIT_WINDOW_KEY)
    sys.exit(-1)

try:
    per_ip = int(sys.argv[1])
except ValueError:
    print "Invalid per ip limit. Must be non zero integer."
    sys.exit(-1)

if per_ip <= 0:
    print "Invalid per ip limit. Must be non zero integer."


try:
    per_token = int(sys.argv[2])
except ValueError:
    print "Invalid per token limit. Must be non zero integer."
    sys.exit(-1)

if per_token <= 0:
    print "Invalid per token limit. Must be non zero integer."


try:
    window = int(sys.argv[3])
except ValueError:
    print "Invalid window size. Must be non zero integer."
    sys.exit(-1)

if window <= 0:
    print "Invalid window size. Must be non zero integer."

r.set(RATELIMIT_PER_TOKEN_KEY, per_token)
r.set(RATELIMIT_PER_IP_KEY, per_ip)
r.set(RATELIMIT_WINDOW_KEY, window)
