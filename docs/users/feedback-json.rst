:orphan:

.. _feedback-json-doc:

Feedback JSON Documentation
===========================

Submission JSON
---------------

To submit recording feedback via our API (see: :doc:`api/recordings`), ``POST`` a JSON document to
the ``recording-feedback`` endpoint.

A sample feedback may look like:

.. code-block:: json

    {
        "recording_mbid": "9f24c0f7-a644-4074-8fbd-a1dba03de129",
        "score": 1
    }


.. code-block:: json

    {
        "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
        "score": 1
    }


.. code-block:: json

    {
        "recording_mbid": "9f24c0f7-a644-4074-8fbd-a1dba03de129",
        "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
        "score": 1
    }

Score can have one of these three values:

- ``1``: Mark the track as loved

   - Indicates user has marked the recording as loved

- ``-1``: Mark the track as hated

   - Indicates user has marked the recording as hated

- ``0``: Remove the feedback from the track

   - Indicates user wants to remove the feedback (loved or hated) from the recording


Fetching feedback JSON
----------------------

The JSON documents returned from our API for recording feedback look like the following:

.. code-block:: json

    {
        "count": 1,
        "feedback": [
            {
                "user_id": "-- the MusicBrainz ID of the user --",
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "recording_msid": "9f24c0f7-a644-4074-8fbd-a1dba03de129",
                "score": 1
            },
            "-- more feedback data here ---"
        ],
        "offset": 0,
        "total_count": 1
    }

The number of feedback items in the document are returned by the top-level ``count`` element. The total number of
feedback items for the user/recording are returned by the top-level ``total_count``. ``offset`` specifies the
number of feedback to skip from the beginning, for pagination.  The other element is the ``feedback`` element.
This is a list which contains the feedback JSON elements having a ``user_id`` the MusicBrainz ID of the user,
a ``recording_msid``, a ``recording_mbid`` and a ``score`` key.
