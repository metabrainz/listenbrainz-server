ListenBrainz API
================

All endpoints have this root URL for our current production site.

- **API Root URL**: ``https://api.listenbrainz.org``

.. note::
    All ListenBrainz services are only available on **HTTPS**!


Authentication
--------------

ListenBrainz makes use of private API keys called user tokens to authenticate requests and ensure the proper
access controls on user data. A user token is a unique alphanumeric string linked to a user account. To retrieve
your user token, follow this guide.

Get the User token
~~~~~~~~~~~~~~~~~~

Every account has a User token associated with it, to get the token:

1. Sign up or Log in your an account using this `link`_.
2. Navigate to `settings`_ page to find your user Token (See image below for reference).
  
  .. image:: ../../images/user-profile.png
    :width: 400
    :alt: Screenshot showing the user settings.

3. Copy the User Token to your clipboard.

  .. note:: 
    You may also reset your user token by clicking the Reset token button on the `settings`_ page.

Add the User token to your requests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The user token must be included in the request header for its usage.
To format the header correctly, you can use the following piece of code:

  .. code-block:: python3

    # The following token must be valid, but it doesn't have to be the token of the user you're
    # trying to get the listen history of.
    TOKEN = 'YOUR_TOKEN_HERE'
    AUTH_HEADER = {
      "Authorization": "Token {0}".format(TOKEN)
    }

Then include the formatted header in the request to use it.

  .. code-block:: python3

        response = requests.get(
          ...
          # Your request url and params go here.
          ...
          headers=AUTH_HEADER,
      )

.. note:: 
  A complete usage example for a request employing Authorization headers to make authenticated requests to ListenBrainz
  can be found on the :doc:`API Usage <../api-usage>` page.


Reference
---------

.. toctree::
   :maxdepth: 1

   core
   playlist
   recordings
   statistics
   popularity
   metadata
   social
   recommendation
   art
   settings
   misc


OpenAPI specification
---------------------

Contributor `rain0r <https://github.com/rain0r>`_ went through the trouble of making
an OpenAPI 3 specification for the ListenBrainz API. Many thanks! Check it out here:
`<https://github.com/rain0r/listenbrainz-openapi>`_


Rate limiting
-------------

The ListenBrainz API is rate limited via the use of rate limiting headers that
are sent as part of the HTTP response headers. Each call will include the
following headers:

- **X-RateLimit-Limit**: Number of requests allowed in given time window

- **X-RateLimit-Remaining**: Number of requests remaining in current time
  window

- **X-RateLimit-Reset-In**: Number of seconds when current time window expires
  (*recommended*: this header is resilient against clients with incorrect
  clocks)

- **X-RateLimit-Reset**: UNIX epoch number of seconds (without timezone) when
  current time window expires [#]_

Rate limiting is automatic and the client must use these headers to determine
the rate to make API calls. If the client exceeds the number of requests
allowed, the server will respond with error code ``429: Too Many Requests``.
Requests that provide the *Authorization* header with a valid user token may
receive higher rate limits than those without valid user tokens.

.. [#] Provided for compatibility with other APIs, but we still recommend using
   ``X-RateLimit-Reset-In`` wherever possible

.. _link: https://listenbrainz.org/login/
.. _settings: https://listenbrainz.org/settings/
