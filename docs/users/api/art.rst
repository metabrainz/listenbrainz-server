Art
===

ListenBrainz has a (cover) art infrastructure that creates new cover art from a user's statstics or
a user's instructions on how to composite a cover art grid.

All art endpoints have this root URL for our current production site.

- **ART API Root URL**: ``https://art-api.listenbrainz.org``

.. note::
    All ListenBrainz services are only available on **HTTPS**!

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: art_api_v1
   :include-empty-docstring:
   :undoc-static:

Constants
^^^^^^^^^

Constants that are relevant to using the API:

.. autodata:: listenbrainz.art.cover_art_generator.MIN_IMAGE_SIZE
.. autodata:: listenbrainz.art.cover_art_generator.MAX_IMAGE_SIZE
.. autodata:: listenbrainz.art.cover_art_generator.MIN_DIMENSION
.. autodata:: listenbrainz.art.cover_art_generator.MAX_DIMENSION
.. autodata:: data.model.common_stat.ALLOWED_STATISTICS_RANGE
