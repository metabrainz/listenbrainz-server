Server API
==========

The ListenBrainz server supports the following end-points for submitting and fetching listens. 

All endpoints have this root URL:

**Root URL**: ``https://api.listenbrainz.org/1``

NOTE: All of ListenBrainz services are available on **HTTPS** only!

Reference
---------

API
^^^

.. autoflask:: webserver:create_app()
   :blueprints: api_v1
   :include-empty-docstring:
   :undoc-static:
