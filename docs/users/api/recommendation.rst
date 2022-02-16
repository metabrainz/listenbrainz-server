Recommendations
===============

ListenBrainz uses collaborative filtering to generate recording recommendations, which may be further processed to
generate playlists for users.

Recording Recommendation API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These api endpoints allow to fetch the raw collaborative filtered recording IDs.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: recommendations_cf_recording_v1
   :include-empty-docstring:
   :undoc-static:

Recording Recommendation Feedback API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These api endpoints allow to submit and retrieve feedback for raw collaborative filtered recordings.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: recommendation_feedback_api_v1
   :include-empty-docstring:
   :undoc-static:
