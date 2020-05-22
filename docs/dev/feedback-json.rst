.. _feedback-json-doc:

Feedback JSON Documentation
===========================

Submission JSON
---------------

To submit a feedback via our API (see: :doc:`api`), ``POST`` a JSON document to
the ``submit-feedback`` endpoint.

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

[
  {
  "user_id": "-- the MusicBrainz ID of the user --",
  "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
  "score": 1
  },
  "-- more feedback data here ---"
]

This is a list which contains the feedback JSON elements having a ``user_id`` the MusicBrainz ID of the user,
a ``recording_msid`` and a ``score`` key.
