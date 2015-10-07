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

Constants
^^^^^^^^^

Constants that are releavant to using the API:

.. autodata:: webserver.views.api.MAX_LISTEN_SIZE
.. autodata:: webserver.views.api.MAX_ITEMS_PER_GET
.. autodata:: webserver.views.api.DEFAULT_ITEMS_PER_GET
.. autodata:: webserver.views.api.MAX_TAGS_PER_LISTEN
.. autodata:: webserver.views.api.MAX_TAG_SIZE
