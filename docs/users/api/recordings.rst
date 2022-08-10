Recordings
==========

.. _feedback-api:

Feedback API
^^^^^^^^^^^^

These API endpoints allow to submit and retrieve feedback for a user's recordings

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: feedback_api_v1
   :include-empty-docstring:
   :undoc-static:

Pinned Recording API
^^^^^^^^^^^^^^^^^^^^

These API endpoints allow submitting, deleting, and retrieving ListenBrainz pinned recordings for users.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: pinned_rec_api_bp_v1
   :include-empty-docstring:
   :undoc-static:
