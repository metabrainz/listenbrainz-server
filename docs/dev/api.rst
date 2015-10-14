ListenBrainz API
================

The ListenBrainz server supports the following end-points for submitting and fetching listens. All endpoints have this root URL:

**Root URL**: ``https://api.listenbrainz.org``

NOTE: All of ListenBrainz services are available on **HTTPS** only!

Reference
---------

API Calls
^^^^^^^^^

.. autoflask:: webserver:create_app_rtfd()
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

.. autodata:: webserver.views.api.MAX_LISTEN_SIZE
.. autodata:: webserver.views.api.MAX_ITEMS_PER_GET
.. autodata:: webserver.views.api.DEFAULT_ITEMS_PER_GET
.. autodata:: webserver.views.api.MAX_TAGS_PER_LISTEN
.. autodata:: webserver.views.api.MAX_TAG_SIZE
