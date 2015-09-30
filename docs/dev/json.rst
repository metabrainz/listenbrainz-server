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
  document may not exceed 10,240 bytes in size.

These different types of submissions are defined by the ``listen_type`` element at the top-most level of the submitted 
JSON document. 

Sample listen submit JSON::

    {
        "listen_type": "single",
        "payload": [
            {
                "listened_at": 1443524987,
                "track_metadata": {
                    "additional_info": {
                        "album": "Sexwitch",
                        "artist": "SEXWITCH",
                        "date": "2015",
                        "musicbrainz_albumid": 
                            "177d02ac-3b54-49f5-8757-3632a27786bf",
                        "musicbrainz_artistid": 
                            "2f0a5dae-f331-485a-b467-b3c9d41f490d",
                        "musicbrainz_releasegroupid": 
                            "323d699e-83b0-4baf-8c2a-49be22ed42fe",
                        "musicbrainz_trackid": 
                            "79570db5-350c-470d-afe7-be5ff03f3e5b",
                        "releasetype": "Album",
                        "title": "Ha Howa Ha Howa",
                        "totaltracks": "6",
                        "tracknumber": "1"
                    },
                    "artist_name": "SEXWITCH",
                    "release_name": "Sexwitch",
                    "track_name": "Ha Howa Ha Howa"
                }
            }
        ]
    }

payload JSON
------------

More about payloads
