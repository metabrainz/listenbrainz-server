.. _json-doc:

JSON Documentation
==================

.. note:: Do not submit copyrighted information in these fields!

Submission JSON
---------------

To submit a listen via our API (see: :doc:`api`), ``POST`` a JSON document to
the ``submit-listens`` endpoint. Submit one of three types JSON documents:

- ``single``: Submit single listen

   - Indicates user just finished listening to track

   - ``payload`` should contain information about *exactly one* track

- ``playing_now``: Submit ``playing_now`` notification

   - Indicates that user just began listening to track

   - ``payload`` should contain information about *exactly one* track

   - Submitting ``playing_now`` documents is optional

   - Timestamp must be omitted from a ``playing_now`` submission.

- ``import``: Submit previously saved listens

   - ``payload`` should contain information about *at least one* track

   - submitting multiple listens in one go is allowed, but the complete JSON
     document may not exceed :data:`~webserver.views.api.MAX_LISTEN_SIZE` bytes
     in size

The ``listen_type`` element defines different types of submissions. The element
is placed at the top-most level of the JSON document. The only other required
element is the ``payload`` element. This provides an array of listens – the
payload may be one or mote listens (as designated by ``listen_type``)::

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
              "listening_from": "spotify",
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
      "payload": {
        "count": 25,
        "user_id": "-- the MusicBrainz ID of the user --",
        "listens": [
          "-- listen data here ---"
        ]
      }
    }

The number of listens in the document are returned by the top-level ``count``
element. The ``user_id`` element contains the MusicBrainz ID of the user whose listens are
being returned. The other element is the ``listens`` element. This is a list which contains
the listen JSON elements (described above).

The JSON document returned by the API endpoint for getting tracks being played right now
is the same as above, except that it also contains the ``payload/playing_now`` element as a
boolean set to True.


Payload JSON details
--------------------

A minimal payload must include
``track_metadata/artist_name`` and ``track_metadata/track_name`` elements::

    {
      "track_metadata": {
        "artist_name": "Rick Astley",
        "track_name": "Never Gonna Give You Up",
      }
    }

``artist_name`` and ``track_name`` elements must be simple strings.

The payload will also include the ``listened_at`` element which must be an integer
representing the Unix time when the track was listened to. The only exception to this
rule is when the listen is being played right now and has been retrieved from the
endpoint to get listens being played right now. The ``listened_at`` element will be
absent for such listens.

Add additional metadata you may have for a track to the ``additional_info``
element. Any additional information allows us to better correlate your listen
data to existing MusicBrainz-based data. If you have MusicBrainz IDs available,
submit them!

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
``isrc``                The ISRC code associated with the recording.
``spotify_id``          The Spotify track URL associated with this recording.  e.g.: http://open.spotify.com/track/1rrgWMXGCGHru5bIRxGFV0
``tags``                A list of user defined tags to be associated with this recording. These tags are similar to last.fm tags. For example, you have apply tags such as ``punk``, ``see-live``, ``smelly``. You may submit up to :data:`~webserver.views.api.MAX_TAGS_PER_LISTEN` tags and each tag may be up to :data:`~webserver.views.api.MAX_TAG_SIZE` characters large.
``listening_from``       The source of the listen, i.e the name of the client or service which submits the listen.
======================= ===========================================================================================================================================================================================================================================================================================================================================================================================================

At this point, we are not scrubbing any superflous elements that may be
submitted via the ``additional_info`` element. We're open to see how people
will make use of these unspecified fields and may decide to formally specify or
scrub elements in the future.

Artist Statistics JSON
----------------------
The JSON documents returned from our API look like the following::

   {
     "payload": {
        "user_id": "-- the MusicBrainz ID of the user --",
        "artist": {
           "all_time": {
              "artists": [
                 "-- Artist stats here --"
              ]
           },
           "count": "-- Number of unique artists the user has listened to --"
         },
         "last_updated": "-- Date when the statistics were last updated --"
       }
     }
   }

An sample response from the endpoint may look like::

   {
     "payload": {
       "artist": {
         "all_time": {
           "artists": [
             {
               "artist_mbids": [93e6118e-7fa8-49f6-9e02-699a1ebce105],
               "artist_msid": "d340853d-7408-4a0d-89c2-6ff13e568815",
               "artist_name": "The Local train",
               "listen_count": 385
             },
             {
               "artist_mbids": [ae9ed5e2-4caf-4b3d-9cb3-2ad626b91714],
               "artist_msid": "ba64b195-01dd-4613-9534-bb87dc44cffb",
               "artist_name": "Lenka",
               "listen_count": 333
             },
             {
               "artist_mbids": [cc197bad-dc9c-440d-a5b5-d52ba2e14234],
               "artist_msid": "6599e41e-390c-4855-a2ac-68ee798538b4",
               "artist_name": "Coldplay",
               "listen_count": 321
             },
         },
         "count": 3
       },
       "last_updated": "Sun, 03 May 2020 08:26:01 GMT",
       "user_id": "John Doe"
     }
   }

.. warning::
   The statistics API endpoint is still in beta and the `JSON` format may change in the future.
