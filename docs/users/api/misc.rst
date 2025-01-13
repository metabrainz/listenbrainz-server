Miscellaneous
=============

Various ListenBrainz API endpoints that are not documented elsewhere.

Explore API
^^^^^^^^^^^

These API endpoints allow fetching fresh releases and cover art details for a given color.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: explore_api_v1, fresh_releases_v1
   :include-empty-docstring:
   :undoc-static:

Donors API
^^^^^^^^^^

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: donor_api_v1
   :include-empty-docstring:
   :undoc-static:

Status API
^^^^^^^^^^

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: status_api_v1
   :include-empty-docstring:
   :undoc-static:
