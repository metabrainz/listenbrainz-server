.. _json-doc:

JSON Documentation
==================

.. note:: Do not submit copyrighted information in these fields!

Submission JSON
---------------

To submit a listen via our API (see: :doc:`api/core`), ``POST`` a JSON document to
the ``submit-listens`` endpoint. Submit one of three types of JSON documents:

- ``single``: Submit single listen

   - Indicates user just finished listening to track

   - ``payload`` should contain information about *exactly one* track

- ``playing_now``: Submit ``playing_now`` notification

   - Indicates that user just began listening to track

   - ``payload`` should contain information about *exactly one* track

   - Submitting ``playing_now`` documents is optional

   - Timestamp must be omitted from a ``playing_now`` submission

.. note::

    Playing Now listens are only stored temporarily. A playing now listen must be
    submitted again as a ``single`` or ``import`` for permanent storage.


- ``import``: Submit previously saved listens

   - ``payload`` should contain information about *at least one* track

   - Submitting multiple listens in one request is permitted. There are some
     limitations on the size of a submission. A request must be less than
     :data:`~listenbrainz.webserver.views.api_tools.MAX_LISTEN_PAYLOAD_SIZE`
     bytes, and you can only submit up to
     :data:`~listenbrainz.webserver.views.api_tools.MAX_LISTENS_PER_REQUEST` listens per
     request. Each listen may not exceed
     :data:`~listenbrainz.webserver.views.api_tools.MAX_LISTEN_SIZE` bytes in size

The ``listen_type`` element defines different types of submissions. The element
is placed at the top-most level of the JSON document. The only other required
element is the ``payload`` element. This provides an array of listens – the
payload may be one or more listens (as designated by ``listen_type``):

.. code-block:: json

    {
      "listen_type": "single",
      "payload": [
          "--- listen data here ---"
      ]
    }

A sample listen payload may look like:

.. code-block:: json

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

A complete submit listen JSON document may look like:

.. code-block:: json

    {
      "listen_type": "single",
      "payload": [
        {
          "listened_at": 1443521965,
          "track_metadata": {
            "additional_info": {
              "media_player": "Rhythmbox",
              "submission_client": "Rhythmbox ListenBrainz Plugin",
              "submission_client_version": "1.0",
              "release_mbid": "bf9e91ea-8029-4a04-a26a-224e00a83266",
              "artist_mbids": [
                "db92a151-1ac2-438b-bc43-b82e149ddd50"
              ],
              "recording_mbid": "98255a8c-017a-4bc7-8dd6-1fa36124572b",
              "tags": [ "you", "just", "got", "rick rolled!"],
              "duration_ms": 222000
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

The JSON documents returned from our API look like the following:

.. code-block:: json

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
``track_metadata/artist_name`` and ``track_metadata/track_name`` elements:

.. code-block:: json

    {
      "track_metadata": {
        "artist_name": "Rick Astley",
        "track_name": "Never Gonna Give You Up",
      }
    }

``artist_name`` and ``track_name`` elements must be simple strings.

The payload should also include the ``listened_at`` element, which must be an integer
representing the Unix time when the track was listened to. This should be set to
playback start time of the submitted track. The minimum accepted
value for this field is :data:`~listenbrainz.webserver.views.api_tools.LISTEN_MINIMUM_TS`.
``playing_now`` requests should not have a ``listened_at`` field.

Add additional metadata you may have for a track to the ``additional_info``
element. Any additional information allows us to better correlate your listen
data to existing MusicBrainz-based data. If you have MusicBrainz IDs available,
submit them!

The following optional elements may also be included in the ``track_metadata`` element:

======================= ===========  =========================================================
element                 data type    description
======================= ===========  =========================================================
``release_name``        string       The name of the release this recording was played from.
======================= ===========  =========================================================

The following optional elements may also be included in the ``additional_info`` element.

.. note::

  If you do not have the data for any of the following fields, omit the key entirely:

.. list-table:: Additional Info Fields
   :widths: 25 10 40
   :header-rows: 1

   * - element
     - data type
     - description
   * - ``artist_mbids``
     - array of strings
     - A list of MusicBrainz Artist IDs, one or more Artist IDs may be included here. If you have a complete MusicBrainz artist credit that contains multiple Artist IDs, include them all in this list.
   * - ``release_group_mbid``
     - string
     - A MusicBrainz Release Group ID of the release group this recording was played from.
   * - ``release_mbid``
     - string
     - A MusicBrainz Release ID of the release this recording was played from.
   * - ``recording_mbid``
     - string
     - A MusicBrainz Recording ID of the recording that was played.
   * - ``track_mbid``
     - string
     - A MusicBrainz Track ID associated with the recording that was played.
   * - ``work_mbids``
     - array of strings
     - A list of MusicBrainz Work IDs that may be associated with this recording.
   * - ``tracknumber``
     - string
     - The tracknumber of the recording. This first recording on a release is tracknumber 1.
   * - ``isrc``
     - string
     - The ISRC code associated with the recording.
   * - ``spotify_id``
     - string
     - The Spotify track URL associated with this recording.  e.g.: http://open.spotify.com/track/1rrgWMXGCGHru5bIRxGFV0
   * - ``tags``
     - array of string
     - A list of user-defined folksonomy tags to be associated with this recording. For example, you can apply tags such as ``punk``, ``see-live``, ``smelly``. You may submit up to :data:`~listenbrainz.webserver.views.api_tools.MAX_TAGS_PER_LISTEN` tags and each tag may be up to :data:`~listenbrainz.webserver.views.api_tools.MAX_TAG_SIZE` characters large.
   * - ``media_player``
     - string
     - The name of the program being used to listen to music. Don't include a version number here.
   * - ``media_player_version``
     - string
     - The version of the program being used to listen to music.
   * - ``submission_client``
     - string
     - The name of the client that is being used to submit listens to ListenBrainz. If the media player has the ability to submit listens built-in then this value may be the same as ``media_player``. Don't include a version number here.
   * - ``submission_client_version``
     - string
     - The version of the submission client.
   * - ``music_service``
     - string
     - If the song being listened to comes from an online service, the canonical domain of this service (see below for more details).
   * - ``music_service_name``
     - string
     - If the song being listened to comes from an online service and you don't know the canonical domain, a name that represents the service.
   * - ``origin_url``
     - string
     - If the song of this listen comes from an online source, the URL to the place where it is available. This could be a spotify URL (see ``spotify_id``), a YouTube video URL, a Soundcloud recording page URL, or the full URL to a public MP3 file. If there is a webpage for this song (e.g. Youtube page, Soundcloud page) **do not** try and resolve the URL to an actual audio resource.
   * - ``duration_ms`` and ``duration``
     - integer
     - The duration of the track in milliseconds and seconds respectively. You should only include one of ``duration_ms`` or ``duration``.
.. note::

  **Music service names**

  The ``music_service`` field should be a domain name rather than a textual description or URL. This allows us to refer unambiguously to a service without worrying
  about capitalization or full/short names (such as the difference between "Internet Archive", "The Internet Archive" or "Archive").
  If we use this data on ListenBrainz, we will perform a mapping from the domain name to a canonical name. Below is an example of mappings that we currently support.
  If you are submitting from a service which doesn't appear in this list, you should determine a canonical domain from the domain of the service.
  Only if you cannot determine a domain for the service should you use the text-only ``music_service_name`` field.

  .. list-table:: Music services domain/name mapping
     :widths: 25 50
     :header-rows: 1

     * - domain
       - name
     * - ``spotify.com``
       - Spotify
     * - ``bandcamp.com``
       - Bandcamp
     * - ``youtube.com``
       - YouTube
     * - ``music.youtube.com``
       - YouTube Music
     * - ``deezer.com``
       - Deezer
     * - ``tidal.com``
       - TIDAL
     * - ``music.apple.com``
       - Apple Music
     * - ``archive.org``
       - Internet Archive
     * - ``soundcloud.com``
       - Soudcloud
     * - ``jamendo.com``
       - Jamendo Music
     * - ``play.google.com``
       - Google Play Music


Client Metadata examples
------------------------

Here are a few examples of how to fill in the ``media_player``, ``submission_client`` and ``music_service`` fields based on our
current recommendations.

BrainzPlayer on the ListenBrainz website playing a video from YouTube
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: JSON

  {
    "track_metadata": {
        "additional_info": {
            "media_player": "BrainzPlayer",
            "music_service": "youtube.com",
            "origin_url": "https://www.youtube.com/watch?v=JKFBiaoFHoY",
            "submission_client": "BrainzPlayer"
        },
        "artist_name": "Mdou Moctar",
        "release_name": "Ilana (The Creator)",
        "track_name": "Inizgam"
    }
  }

BrainzPlayer on the ListenBrainz website playing a video from Spotify
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Note that even though the ``origin_url`` is ``https://open.spotify.com``, we set ``music_service``
to spotify.com (see above note).

.. code-block:: JSON

  {
    "track_metadata": {
        "additional_info": {
            "media_player": "BrainzPlayer",
            "music_service": "spotify.com",
            "origin_url": "https://open.spotify.com/track/5fEjp2F0Sqr9fMuLSaDqz0",
            "submission_client": "BrainzPlayer"
        },
        "artist_name": "Les Filles de Illighadad",
        "release_name": "Eghass Malan",
        "track_name": "Inssegh Inssegh"
    }
  }


Using Otter for Funkwhale on Android, and submitting with Simple Scrobbler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this case, the media player and submission client are completely separate programs. Because music is being played
from a user's private collection and not a streaming service, don't include ``music_service`` or ``origin_url``.

.. code-block:: JSON

  {
    "track_metadata": {
        "additional_info": {
            "media_player": "Otter",
            "media_player_version": "1.0.21",
            "submission_client": "Simple Scrobbler"
            "submission_client_version": "1.7.0"
        },
        "artist_name": "Les Filles de Illighadad",
        "release_name": "Eghass Malan",
        "track_name": "Inssegh Inssegh"
    }
  }


Rhythmbox player listening to Jamendo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: JSON

  {
    "track_metadata": {
        "additional_info": {
            "media_player": "Rhythmbox",
            "music_service": "jamendo.com",
            "music_service_name": "Jamendo Music"
            "origin_url": "https://www.jamendo.com/track/1466090/universal-funk",
            "submission_client": "Rhythmbox ListenBrainz Plugin"
        },
        "artist_name": "Duo Teslar",
        "track_name": "Universal Funk"
    }
  }

Listening to a recording from Bandcamp and submitting with the browser extension WebScrobbler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because playback happens in the browser, there is no specific ``media_player``.

.. code-block:: JSON

  {
	"track_metadata": {
		"additional_info": {
			"music_service": "bandcamp.com",
			"music_service_name": "Bandcamp",
			"submission_client": "WebScrobbler",
			"submission_client_version": "v2.48.0"
			"origin_url": "https://greencookierecords.bandcamp.com/track/shake",
		},
		"artist_name": "I Mitomani Beat",
		"release_name": "Fuori Dal Tempo",
		"track_name": "Shake",
	}
  }

At this point, we are not removing any other elements that may be
submitted via the ``additional_info`` element. We're open to see how people
will make use of these unspecified fields and may decide to formally specify or
scrub elements in the future.
