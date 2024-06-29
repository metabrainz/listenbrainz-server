Core
====

The ListenBrainz server supports the following end-points for submitting and fetching listens.

.. autoflask:: listenbrainz.webserver:create_app_rtfd()
   :blueprints: api_v1
   :include-empty-docstring:
   :undoc-static:
   :undoc-endpoints: api_v1.latest_import

.. http:get:: /1/latest-import

  Get the timestamp of the newest listen submitted by a user in previous imports to ListenBrainz.

  In order to get the timestamp for a user, make a GET request to this endpoint. The data returned will
  be JSON of the following format:

  .. code-block:: json

      {
          "musicbrainz_id": "the MusicBrainz ID of the user",
          "latest_import": "the timestamp of the newest listen submitted in previous imports. Defaults to 0"
      }

  :query str user_name: the MusicBrainz ID of the user whose data is needed
  :statuscode 200: Yay, you have data!
  :resheader Content-Type: *application/json*

.. http:post:: /1/latest-import

  Update the timestamp of the newest listen submitted by a user in an import to ListenBrainz.

  In order to update the timestamp of a user, you'll have to provide a user token in the Authorization Header. User tokens can be found on https://listenbrainz.org/settings/.

  The JSON that needs to be posted must contain a field named `ts` in the root with a valid unix timestamp. Example:

  .. code-block:: json

     {
        "ts": 0
     }

  :reqheader Authorization: Token <user token>
  :statuscode 200: latest import timestamp updated
  :statuscode 400: invalid JSON sent, see error message for details.
  :statuscode 401: invalid authorization. See error message for details.

Timestamps
^^^^^^^^^^

All timestamps used in ListenBrainz are UNIX epoch timestamps in UTC. When
submitting timestamps to us, please ensure that you have no timezone
adjustments on your timestamps.

Constants
^^^^^^^^^

Constants that are relevant to using the API:

.. autodata:: listenbrainz.webserver.views.api_tools.MAX_LISTEN_PAYLOAD_SIZE
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_LISTEN_SIZE
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_DURATION_LIMIT
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_DURATION_MS_LIMIT
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_LISTENS_PER_REQUEST
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_ITEMS_PER_GET
.. autodata:: listenbrainz.webserver.views.api_tools.DEFAULT_ITEMS_PER_GET
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_TAGS_PER_LISTEN
.. autodata:: listenbrainz.webserver.views.api_tools.MAX_TAG_SIZE
.. autodata:: listenbrainz.listenstore.LISTEN_MINIMUM_TS
