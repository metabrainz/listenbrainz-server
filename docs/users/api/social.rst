Social
======

User Timeline API
^^^^^^^^^^^^^^^^^

These api endpoints allow to create and fetch timeline events for a user.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: user_timeline_event_api_bp

Follow API
^^^^^^^^^^

These apis allow to interact with follow user feature of ListenBrainz.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: social_api_v1
   :include-empty-docstring:
   :undoc-static:
