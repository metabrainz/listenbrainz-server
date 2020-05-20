.. _feedback-json-doc:

Feedback JSON Documentation
===========================

.. note:: Do not submit copyrighted information in these fields!

Submission JSON
---------------

To submit a feedback via our API (see: :doc:`api`), ``POST`` a JSON document to
the ``submit-feedback`` endpoint. Submit JSON document of the following type:

- ``feedback``: Submit feedback for a recording

   - ``payload`` should contain information about *exactly one* recording feedback

   - The complete JSON document may not exceed :data:`~webserver.views.api.MAX_FEEDBACK_SIZE` 
     bytes in size


The ``submission_type`` element defines different types of submissions. The element
is placed at the top-most level of the JSON document. The only other required
element is the ``payload`` element. This provides an array of feedbacks – the
payload must contain only one feedback

A sample feedback payload may look like::

    {
        "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
        "score": +1
    }

Score can have one of these three values:

- ``1``: Mark the track as loved

   - Indicates user has marked the recording as loved

- ``-1``: Mark the track as hated

   - Indicates user has marked the recordings as hated

- ``0``: Remove the feedback from the track

   - Indicates user wants to remove the feedback (loved or hated) from the recording

A complete submit listen JSON document may look like::

    {
      "submission_type": "feedback",
      "payload": [
        {
        "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
        "score": +1
        }
      ]
    }


Fetching feedback JSON
----------------------

The JSON documents returned from our API for feedbacks given by a user look
like the following::

    {
      "payload": {
        "count": 25,
        "user_id": "-- the MusicBrainz ID of the user --",
        "feedbacks": [
          {
          "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
          "score": +1
          },
          "-- more feedback data here ---"
        ]
      }
    }

The number of feedbacks in the document are returned by the top-level ``count``
element. The ``user_id`` element contains the MusicBrainz ID of the user whose feedbacks are
being returned. The other element is the ``feedbacks`` element. This is a list which contains
the feedback JSON elements having a ``recording_msid`` and a ``score`` key.

The JSON documents returned from our API for feedbacks given for a recording look
like the following::

    {
      "payload": {
        "count": 25,
        "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
        "feedbacks": [
          {
          "user_id": "-- the MusicBrainz ID of the user --",
          "score": +1
          },
          "-- more feedback data here ---"
        ]
      }
    }

The number of feedbacks in the document are returned by the top-level ``count``
element. The ``recording_msid`` element contains the MeesyBrainz ID of the recording 
whose feedbacks are being returned. The other element is the ``feedback`` element. 
This is a list which contains the feedback JSON elements having a ``user_id`` 
and a ``score`` key.
