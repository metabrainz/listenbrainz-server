.. _feedback-json-doc:

Feedback JSON Documentation
===========================

.. note:: Do not submit copyrighted information in these fields!

Submission JSON
---------------

To submit a feedback via our API (see: :doc:`api`), ``POST`` a JSON document to
the ``submit-feedback`` endpoint.

   - The complete JSON document may not exceed :data:`~webserver.views.api.MAX_FEEDBACK_SIZE` 
     bytes in size


A sample feedback may look like::

    {
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

The JSON documents returned from our API for user feedback look like the following::

    {
      "user_id": "-- the MusicBrainz ID of the user --",
      "feedback": [
        {
        "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
        "score": 1
        },
        "-- more feedback data here ---"
      ]
    }

The ``user_id`` element contains the MusicBrainz ID of the user whose feedback are
being returned. The other element is the ``feedback`` element. This is a list which contains
the feedback JSON elements having a ``recording_msid`` and a ``score`` key.

The JSON documents returned from our API for recording feedback look like the following::

    {
      "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
      "feedback": [
        {
        "user_id": "-- the MusicBrainz ID of the user --",
        "score": 1
        },
        "-- more feedback data here ---"
      ]
    }

The ``recording_msid`` element contains the MessyBrainz ID of the recording 
whose feedback are being returned. The other element is the ``feedback`` element. 
This is a list which contains the feedback JSON elements having a ``user_id`` 
and a ``score`` key.
