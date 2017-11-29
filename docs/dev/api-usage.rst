.. role:: json(code)
   :language: json

.. role:: py(code)
   :language: python

API Usage Examples
==================

.. note::

   These examples are written in Python version **3.6.3** and use `requests
   <http://docs.python-requests.org/en/master/>`_ version **2.18.4**.

Prerequisites
#############

All the examples assume you have a development version of the ListenBrainz
server set up on :code:`localhost`. Remember to set :code:`DEBUG` to :py:`True`
in the config. When in production, you can replace :code:`localhost` with
:code:`api.listenbrainz.org` to use the real API. In order to use either one,
you'll need a token. You can find it under :code:`ROOT/profile/` when signed
in, with :code:`ROOT` being either :code:`localhost` for the dev version or
:code:`listenbrainz.org` for the real API.

.. caution::

   You should use the token from the API you're using. In production, change the
   token to one from :code:`listenbrainz.org`.

If you want to run the samples, you'll need to add the imports from this common
file that are required by each sample:

.. include:: ./api_usage_examples/common.py
   :code: python

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

.. code::

    Track: Never Gonna Give You Up, listened at 1512040365
    Track: Never Gonna Give You Up, listened at 1511977429
    Track: Never Gonna Give You Up, listened at 1511968583
    Track: Never Gonna Give You Up, listened at 1443521965
    Track: Never Gonna Give You Up, listened at 42042042

.. include:: ./api_usage_examples/get_listens.py
   :code: python

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

You should see output like this:

.. code::

   User naiveaiguy last imported on 30 11 2017 at 12:23

.. include:: ./api_usage_examples/get_latest_import.py
   :code: python
