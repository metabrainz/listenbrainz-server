.. _json-doc:

JSON Documentation
==================

submission JSON
---------------

To submit a listen via our :doc:`api` you'll need to POST a JSON document to the ``submit-listens`` endpoint. You
can submit one of three types JSON documents:

* ``single`` - submit a single listen. This indicates that the user just finished listening to this track. Only
  a single track may be specified in the ``payload``.
* ``playing_now`` - submit a playing_now notification; This indicates that the user just began listening to this 
  track. The ``payload`` may contain only one track and submitting ``playing_now`` documents is optional.
* ``import`` - submit previously saved listens; the ``payload`` may contain more than one listen, but the complete
  document may not exceed :data:`~webserver.views.api.MAX_LISTEN_SIZE` bytes in size.

These different types of submissions are defined by the ``listen_type`` element at the top-most level of the submitted 
JSON document. The only other element required at the top level is the payload element that provides an array of
listens -- the payload may be one or more listens (as designated by the listen_type)::

    {
      "listen_type": "single",
      "payload": [
          --- listen data here ---
      ]
    }

A sample listen payload may look like::

    {
      "listened_at": 1443521965,
      "track_metadata": {
        "additional_info": {
          "release_mbid": "bf9e91ea-8029-4a04-a26a-224e00a83266",
          "artist_mbids": [
            "db92a151-1ac2-438b-bc43-b82e149ddd50"
          ],
          "recording_mbid": "98255a8c-017a-4bc7-8dd6-1fa36124572b",
          "tags": [ "you", "just", "got", "rick rolled!"]
        },
        "artist_name": "Rick Astley",
        "track_name": "Never Gonna Give You Up",
        "release_name": "Whenever you need somebody"
      }
    }

A complete submit listen JSON document may look like::

    {
      "listen_type": "single",
      "payload": [
        {
          "listened_at": 1443521965,
          "track_metadata": {
            "additional_info": {
              "release_mbid": "bf9e91ea-8029-4a04-a26a-224e00a83266",
              "artist_mbids": [
                "db92a151-1ac2-438b-bc43-b82e149ddd50"
              ],
              "recording_mbid": "98255a8c-017a-4bc7-8dd6-1fa36124572b",
              "tags": [ "you", "just", "got", "rick rolled!"]
            },
            "artist_name": "Rick Astley",
            "track_name": "Never Gonna Give You Up",
            "release_name": "Whenever you need somebody"
          }
        }
      ]
    }


fetching listen JSON
--------------------

The JSON documents returned from our API look like the following::

    {
      "count": 25,
      "payload": [
          --- listen data here ---
      ]
    }

The top level count element indicates how many listens are returned in this document. The other element is the payload element, which contains
listen JSON elements as described above.

payload JSON details
--------------------

More about payloads -- TBC.
