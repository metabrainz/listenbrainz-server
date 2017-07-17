ListenBrainz API for Beta
=========================

The ListenBrainz server supports the following end-points for submitting and fetching listens. 
All endpoints have this root URL for our current "pre-beta" site:

**Beta API Root URL**: ``https://beta-api.listenbrainz.org``
**Beta Web Root URL**: ``https://beta.listenbrainz.org``

Once we go to a full beta, we're going to move to the production URLs:

**Production API Root URL**: ``https://api.listenbrainz.org``
**Production Web Root URL**: ``https://listenbrainz.org``

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
