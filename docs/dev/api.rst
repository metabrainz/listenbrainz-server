ListenBrainz API
================

The ListenBrainz server supports the following end-points for submitting and fetching listens. All endpoints have this root URL:

**Root URL**: ``https://api.listenbrainz.org``

NOTE: All of ListenBrainz services are available on **HTTPS** only!

Reference
---------

API Calls
^^^^^^^^^

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: api_v1
   :include-empty-docstring:
   :undoc-static:

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
