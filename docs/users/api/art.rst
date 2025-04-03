.. role:: html(code)
   :language: html


Art
===

ListenBrainz has a (cover) art infrastructure that creates new cover art from a user's statistics or
a user's instructions on how to composite a cover art grid.

As these endpoints return SVGs rather than images, you must embed them in an html :html:`<object data="covert_art_url" type="image/svg+xml">`
element rather than an :html:`<img src="covert_art_url">` element. Otherwise external resources such as cover art images
and fonts will not be loaded and the result will be useless.

See https://developer.mozilla.org/en-US/docs/Web/HTML/Element/object for reference.

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
   :no-index:
