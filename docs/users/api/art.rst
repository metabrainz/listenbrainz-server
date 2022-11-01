Art
===

ListenBrainz has a (cover) art infrastructure that creates new cover art from a users' statstics or
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

.. autodata:: art.cover_art_generator.CoverArtGenerator.MIN_IMAGE_SIZE
.. autodata:: art.cover_art_generator.CoverArtGenerator.MAX_IMAGE_SIZE
