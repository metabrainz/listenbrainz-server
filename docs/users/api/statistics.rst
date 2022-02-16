Statistics
==========

ListenBrainz has a statistics infrastructure that collects and computes statistics
from the listen data that has been stored in the database. The endpoints in this section
offer a way to get this data programmatically.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: stats_api_v1
   :include-empty-docstring:
   :undoc-static:

Constants
^^^^^^^^^

Constants that are relevant to using the API:

.. autodata:: data.model.common_stat.ALLOWED_STATISTICS_RANGE
