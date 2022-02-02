Miscellaneous
=============

Various ListenBrainz API endpoints that are not documented elsewhere.

Color API
^^^^^^^^^

These API endpoints allow fetching releases with recordings and cover art details for a given color.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: color_api_v1
   :include-empty-docstring:
   :undoc-static:

Status API
^^^^^^^^^^

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: status_api_v1
   :include-empty-docstring:
   :undoc-static:
