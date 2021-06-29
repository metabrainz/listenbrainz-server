ListenBrainz API
================

The ListenBrainz server supports the following end-points for submitting and
fetching listens. All endpoints have this root URL for our current production
site [#]_.

- **API Root URL**: ``https://api.listenbrainz.org``

- **Web Root URL**: ``https://listenbrainz.org``

*Note*: All ListenBrainz services are only available on **HTTPS**!

Reference
---------

Core API Endpoints
^^^^^^^^^^^^^^^^^^

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: api_v1
   :include-empty-docstring:
   :undoc-static:
   :undoc-endpoints: api_v1.latest_import, api_v1.user_feed

.. http:get:: /1/latest-import

  Get the timestamp of the newest listen submitted by a user in previous imports to ListenBrainz.

  In order to get the timestamp for a user, make a GET request to this endpoint. The data returned will
  be JSON of the following format:

  .. code-block:: json

      {
          "musicbrainz_id": "the MusicBrainz ID of the user",
          "latest_import": "the timestamp of the newest listen submitted in previous imports. Defaults to 0"
      }

  :query str user_name: the MusicBrainz ID of the user whose data is needed
  :statuscode 200: Yay, you have data!
  :resheader Content-Type: *application/json*

.. http:post:: /1/latest-import

  Update the timestamp of the newest listen submitted by a user in an import to ListenBrainz.

  In order to update the timestamp of a user, you'll have to provide a user token in the Authorization Header. User tokens can be found on https://listenbrainz.org/profile/.

  The JSON that needs to be posted must contain a field named `ts` in the root with a valid unix timestamp. Example:

  .. code-block:: json

     {
        "ts": 0
     }

  :reqheader Authorization: Token <user token>
  :statuscode 200: latest import timestamp updated
  :statuscode 400: invalid JSON sent, see error message for details.
  :statuscode 401: invalid authorization. See error message for details.

Playlists API Endpoints
^^^^^^^^^^^^^^^^^^^^^^^
The playlists API allows for the creation and editing of lists of recordings

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: playlist_api_v1
   :include-empty-docstring:
   :undoc-static:

Feedback API Endpoints
^^^^^^^^^^^^^^^^^^^^^^
These API endpoints allow to submit and retrieve feedback for a user's recordings

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: feedback_api_v1
   :include-empty-docstring:
   :undoc-static:

Recording Recommendation API Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ListenBrainz uses collaborative filtering to generate recording recommendations,
which may be further processed to generate playlists for users. These api endpoints
allow to fetch the raw collaborative filtered recording IDs.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: recommendations_cf_recording_v1
   :include-empty-docstring:
   :undoc-static:

Recording Recommendation Feedback API Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ListenBrainz uses collaborative filtering to generate recording recommendations,
which may be further processed to generate playlists for users. These api endpoints
allow to submit and retrieve feedback for raw collaborative filtered recordings.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: recommendation_feedback_api_v1
   :include-empty-docstring:
   :undoc-static:

Statistics API Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^
ListenBrainz has a statistics infrastructure that collects and computes statistics
from the listen data that has been stored in the database. The endpoints in this section
offer a way to get this data programmatically.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: stats_api_v1
   :include-empty-docstring:
   :undoc-static:

Status API Endpoints
^^^^^^^^^^^^^^^^^^^^

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: status_api_v1
   :include-empty-docstring:
   :undoc-static:

User Timeline API Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
These api endpoints allow to create and fetch timeline events for a user.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: user_timeline_event_api_bp

Social API Endpoints
^^^^^^^^^^^^^^^^^^^^
These apis allow to interact with social features of ListenBrainz.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: social_api_v1
   :include-empty-docstring:
   :undoc-static:

Pinned Recording API Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
These API endpoints allow submitting, deleting, and retrieving ListenBrainz pinned recordings for users.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: pinned_rec_api_bp_v1
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
  current time window expires [#]

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

Constants that are relevant to using the API:

.. autodata:: listenbrainz.webserver.views.api_tools.MAX_LISTEN_SIZE
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_ITEMS_PER_GET
.. autodata:: listenbrainz.webserver.views.api_tools.DEFAULT_ITEMS_PER_GET
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_TAGS_PER_LISTEN
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_TAG_SIZE
