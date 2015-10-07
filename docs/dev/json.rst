.. _json-doc:

JSON Documentation
==================

Submission JSON
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


Fetching listen JSON
--------------------

The JSON documents returned from our API look like the following::

    {
      "count": 25,
      "payload": [
          "-- listen data here ---"
      ]
    }

The top level count element indicates how many listens are returned in this document. The other element is the payload element, which contains
listen JSON elements as described above.

Payload JSON details
--------------------

A minimal payload must include the ``listened_at``, ``track_metadata/artist_name`` and ``track_metadata/track_name``
elements::

    {
      "listened_at": 1443521965,
      "track_metadata": {
        "artist_name": "Rick Astley",
        "track_name": "Never Gonna Give You Up",
      }
    }

We strongly recommend to add whatever additional metadata you may have for a track to the ``additional_info`` element.
Any additional information will allow us to better correlate your listen data to existing MusicBrainz based data. If you
have MusicBrainz IDs availble, submit them!

The following optional elements may also be included in the ``track_metadata`` element:

======================= ===========================================================================================================================================================================================================================================================================================================================================================================================================
element                 description
======================= ===========================================================================================================================================================================================================================================================================================================================================================================================================
``release_name``        the name of the release this recording was played from.
======================= ===========================================================================================================================================================================================================================================================================================================================================================================================================

The following optional elements may also be included in the ``additional_info`` element. If you do not have
the data for any of the following fields, omit the key entirely:

======================= ===========================================================================================================================================================================================================================================================================================================================================================================================================
element                 description
======================= ===========================================================================================================================================================================================================================================================================================================================================================================================================
``artist_mbids``        A list of MusicBrainz Artist IDs, one or more Artist IDs may be included here. If you have a complete MusicBrainz artist credit that contains multiple Artist IDs, include them all in this list.
``release_group_mbid``  A MusicBrainz Release Group ID of the release group this recording was played from.
``release_mbid``        A MusicBrainz Release ID of the release this recording was played from.
``recording_mbid``      A MusicBrainz Recording ID of the recording that was played.
``track_mbid``          A MusicBrainz Track ID associated with the recording that was played.
``work_mbids``          A list of MusicBrainz Work IDs that may be associated with this recording.
``tracknumber``         The tracknumber of the recording. This first recording on a release is tracknumber 1.
``spotify_id``          The Spotify track URL associated with this recording.  e.g.: http://open.spotify.com/track/1rrgWMXGCGHru5bIRxGFV0
``tags``                A list of user defined tags to be associated with this recording. These tags are similar to last.fm tags. For example, you have apply tags such as ``punk``, ``see-live``, ``smelly``. You may submit up to :data:`~webserver.views.api.MAX_TAGS_PER_LISTEN` tags and each tag may be up to :data:`~webserver.views.api.MAX_TAG_SIZE` characters large.
======================= ===========================================================================================================================================================================================================================================================================================================================================================================================================

At this point, we are not scrubbing any superflous elements that may be submitted via the ``additional_info`` element. We're
open to see how people will make use of these unspecified fields and may decide to formally specify or scrub elements in
the future. 

**Please do not submit copyrighted information in these fields!!**
