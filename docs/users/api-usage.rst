.. role:: json(code)
   :language: json

.. role:: py(code)
   :language: python

Usage Examples
==============

.. note::

   These examples are written in Python version **3.6.3** and use `requests
   <http://docs.python-requests.org/en/master/>`_ version **2.18.4**.

Prerequisites
#############

All the examples assume you have a development version of the ListenBrainz
server set up on :code:`localhost`. Remember to set :code:`DEBUG` to :py:`True`
in the config. When in production, you can replace :code:`localhost` with
:code:`api.listenbrainz.org` to use the real API. In order to use either one,
you'll need a token. You can find it under :code:`ROOT/settings/` when signed
in, with :code:`ROOT` being either :code:`localhost` for the dev version or
:code:`listenbrainz.org` for the real API.

.. caution::

   You should use the token from the API you're using. In production, change the
   token to one from :code:`listenbrainz.org`.

Examples
########

Submitting Listens
------------------

See :ref:`json-doc` for details on the format of the Track dictionaries.

If everything goes well, the json response should be :json:`{"status": "ok"}`,
and you should see a recent listen of "Never Gonna Give You Up" when you visit
:code:`ROOT/user/{your-user-name}`.

.. include:: ./api_usage_examples/submit_listens.py
   :code: python

Getting Listen History
----------------------

See :ref:`json-doc` for details on the format of the Track dictionaries.

If there's nothing in the listen history of your user, you can run
:code:`submit_listens` before this.

If there is some listen history, you should see a list
of tracks like this:

.. include:: ./api_usage_examples/get_listens.py
   :code: python

.. code::

    Track: Never Gonna Give You Up, listened at 1512040365
    Track: Never Gonna Give You Up, listened at 1511977429
    Track: Never Gonna Give You Up, listened at 1511968583
    Track: Never Gonna Give You Up, listened at 1443521965
    Track: Never Gonna Give You Up, listened at 42042042

Lookup MBIDs
------------

To interact with various ListenBrainz features, you will often need a MBID of
the recording of a listen. You can use the :ref:`metadata-api` endpoints to
lookup MBID and additional metadata for the listen using its track name and
artist name. For instance,

.. include:: ./api_usage_examples/lookup_metadata.py
   :code: python

Please provide the prompted data to the script to lookup the given track. Currently the release
argument for a listen is not used, but we plan to support in the near future, so we encourage
you to start sending release information if you have it.

.. code-block:: json

  {
      "artist_credit_name": "Ariana Grande",
      "artist_mbids": [
          "f4fdbb4c-e4b7-47a0-b83b-d91bbfcfa387"
      ],
      "metadata": {
          "recording": {
              "rels": [
                  {
                      "artist_mbid": "eb811bf7-4c99-4781-84c0-10ba6b8e33b3",
                      "artist_name": "Carl Falk",
                      "instrument": "guitar",
                      "type": "instrument"
                  },
                  {
                      "artist_mbid": "c8af4490-e48a-4f91-aef9-2b1e39369576",
                      "artist_name": "Savan Kotecha",
                      "instrument": "background vocals",
                      "type": "vocal"
                  },
                  {
                      "artist_mbid": "0d33cc88-28ae-44d5-be7e-7a653e518720",
                      "artist_name": "Jeanette Olsson",
                      "instrument": "background vocals",
                      "type": "vocal"
                  }
              ]
          }
      },
      "recording_mbid": "9f24c0f7-a644-4074-8fbd-a1dba03de129",
      "recording_name": "One Last Time",
      "release_mbid": "be5d97b1-408a-4e95-b924-0a61955048de",
      "release_name": "My Everything"
  }

Love/hate feedback
------------------

To provide love/hate feedback on listens, you need a recording mbid. If you do not
have a recording mbid, you can look it up using the metadata endpoints. See `Lookup MBIDs`_
for an example of the same. Here is an example of how to submit love/hate feedback using
the ListenBrainz API. Refer to :ref:`feedback-api` for more details.

.. include:: ./api_usage_examples/submit_feedback.py
   :code: python

Please provide the prompted data to the script to submit feedback.

Latest Import
-------------

Set and get the timestamp of the latest import into ListenBrainz.

Setting
^^^^^^^

.. include:: ./api_usage_examples/set_latest_import.py
   :code: python

Getting
^^^^^^^

If your user has never imported before and the latest import has never been
set by a script, then the server will return :code:`0` by default. Run
:code:`set_latest_import` before this if you don't want to actually import any
data.

.. include:: ./api_usage_examples/get_latest_import.py
   :code: python

You should see output like this:

.. code::

   User naiveaiguy last imported on 30 11 2017 at 12:23
