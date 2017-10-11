ListenBrainz API for Beta
=========================

The ListenBrainz server supports the following end-points for submitting and
fetching listens.  All endpoints have this root URL for our current production
site [#]_.

- **API Root URL**: ``https://api.listenbrainz.org``

- **Web Root URL**: ``https://listenbrainz.org``

*Note*: All ListenBrainz services are only available on **HTTPS**!

.. [#] The beta endpoints (i.e. ``beta.listenbrainz.org`` was deprecated in
   Fall 2017. If you were using this endpoint, please use the current,
   production endpoints instead.

Reference
---------

API Calls
^^^^^^^^^

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: api_v1
   :include-empty-docstring:
   :undoc-static:

Rate limiting
^^^^^^^^^^^^^

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

Timestamps
^^^^^^^^^^

All timestamps used in ListenBrainz are UNIX epoch timestamps in UTC. When
submitting timestamps to us, please ensure that you have no timezone
adjustments on your timestamps.

Constants
^^^^^^^^^

Constants that are releavant to using the API:

.. autodata:: listenbrainz.webserver.views.api_tools.MAX_LISTEN_SIZE
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_ITEMS_PER_GET
.. autodata:: listenbrainz.webserver.views.api_tools.DEFAULT_ITEMS_PER_GET
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_TAGS_PER_LISTEN
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_TAG_SIZE

