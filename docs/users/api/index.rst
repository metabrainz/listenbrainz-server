ListenBrainz API
================

All endpoints have this root URL for our current production site.

- **API Root URL**: ``https://api.listenbrainz.org``

.. note::
    All ListenBrainz services are only available on **HTTPS**!

Reference
---------

.. toctree::
   :maxdepth: 1

   core
   playlist
   recordings
   statistics
   metadata
   social
   recommendation
   art
   misc


Rate limiting
-------------

The ListenBrainz API is rate limited via the use of rate limiting headers that
are sent as part of the HTTP response headers. Each call will include the
following headers:

- **X-RateLimit-Limit**: Number of requests allowed in given time window

- **X-RateLimit-Remaining**: Number of requests remaining in current time
  window

- **X-RateLimit-Reset-In**: Number of seconds when current time window expires
  (*recommended*: this header is resilient against clients with incorrect
  clocks)

- **X-RateLimit-Reset**: UNIX epoch number of seconds (without timezone) when
  current time window expires [#]_

Rate limiting is automatic and the client must use these headers to determine
the rate to make API calls. If the client exceeds the number of requests
allowed, the server will respond with error code ``429: Too Many Requests``.
Requests that provide the *Authorization* header with a valid user token may
receive higher rate limits than those without valid user tokens.

.. [#] Provided for compatibility with other APIs, but we still recommend using
   ``X-RateLimit-Reset-In`` wherever possible
