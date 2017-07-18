ListenBrainz API for Beta
=========================

The ListenBrainz server supports the following end-points for submitting and fetching listens. 
All endpoints have this root URL for our current "pre-beta" site:

* **Beta API Root URL**: ``https://beta-api.listenbrainz.org``
* **Beta Web Root URL**: ``https://beta.listenbrainz.org``

Once we go to a full beta, we're going to move to the production URLs:

* **Production API Root URL**: ``https://api.listenbrainz.org``
* **Production Web Root URL**: ``https://listenbrainz.org``

The current site at listenbrainz.org will move to alpha.listenbrainz.org once we're in beta.

NOTE: All of ListenBrainz services are available on **HTTPS** only!

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

The ListenBrainz API is rate limited via the use of rate limiting headers that are sent as part of
the HTTP response headers. Each call will include the following headers:

* **X-RateLimit-Limit**: The number of requests allowed in a given time window.
* **X-RateLimit-Remaining**: The number of requests remaining in the current time window.
* **X-RateLimit-Reset-In**: The number of seconds when the current time window expires. We recommend you use this header, since it is resilient against clients with incorrect clocks.
* **X-RateLimit-Reset**: The UNIX epoch number of seconds (without timezone) when the current time window expires. This is provided for compatibility with other APIs, but we recommend using the X-Ratelimit-Reset-In header.

The rate limiting is automatic and the client must use these headers to determine the rate at which calls to the API can be made.
If the client exceeds the number of requests allowed, the server will respond with error code **429** *Too Many Requests*. Requests that provide
the *Authorization* header with a valid user token may receive higher rate limits than those without valid user tokens.


Timestamps
^^^^^^^^^^

All timestamps used in this project are UNIX epoch timestamps in UTC. When submitting timestamps to us,
please ensure that you have no timezone adjustments on your timestamps.

Constants
^^^^^^^^^

Constants that are releavant to using the API:

.. autodata:: listenbrainz.webserver.views.api_tools.MAX_LISTEN_SIZE
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_ITEMS_PER_GET
.. autodata:: listenbrainz.webserver.views.api_tools.DEFAULT_ITEMS_PER_GET
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_TAGS_PER_LISTEN
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_TAG_SIZE
