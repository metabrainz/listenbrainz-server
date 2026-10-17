Connecting music services from another application
==================================================

ListenBrainz can import a user's listening history from music services such as Spotify. The
connection to those services is made with OAuth, and one of the security measures in OAuth
is the session state protecting the authorization request. That state can only be created
on the domain that initiates the request, in this case ``listenbrainz.org``, so another
application cannot start the flow on ListenBrainz's behalf.

Instead, a third party application sends the user to ListenBrainz, ListenBrainz creates the
session state and runs the whole OAuth dance with the music service, stores the resulting
tokens and then sends the user back to the application that started the flow::

    your app  ──▶  listenbrainz.org/connect/spotify/  ──▶  accounts.spotify.com
                       (confirmation page)                          │
    your app  ◀──  listenbrainz.org/settings/…/callback/  ◀─────────┘

The user is never logged in to ListenBrainz along the way — you tell us who they are in
advance with a MetaBrainz OAuth access token. Because of that, ListenBrainz shows them one
page before handing them on to the music service: it names your application and the host
they will be returned to, names the ListenBrainz account the music service would be
connected to, and asks them to confirm. That page is the only point in the flow where they are told which account this
is for, so it cannot be skipped. Everything after it is a plain redirect.

Getting access
--------------

There is nothing to register with ListenBrainz. The ``listenbrainz:connect-services``
scope is only granted to applications MetaBrainz has approved for it, and an access token
carrying that scope is the whole of the authorization — there is no separate ListenBrainz
``client_id`` or ``client_secret``. Apply to MetaBrainz for the scope.

The name shown to your users on the confirmation page is the one your application is
registered under with MetaBrainz, so make sure it is a name they will recognise.

Because there is no registered list of redirect uris to match against, ``redirect_uri`` is
whatever you send, as long as it is an absolute ``https`` url (``http`` is accepted only
for ``localhost``, for local development).

Starting the flow
-----------------

Ask your user for a MetaBrainz OAuth access token with the
``listenbrainz:connect-services`` scope, then post it from your backend:

.. code-block:: none

    POST https://listenbrainz.org/connect/<service>/
    Authorization: Bearer <MetaBrainz OAuth access token>
    Content-Type: application/json

    {
        "redirect_uri": "https://your.app/listenbrainz/connected",
        "state": "...",
        "permissions": "import"
    }

``<service>`` is ``spotify``. It is the only service this flow supports at the moment;
anything else is rejected with a ``400``.

:json redirect_uri: **(required)** Where the user is sent once the flow finishes. It has
    to be an absolute ``https`` url. Its host is shown to the user on the confirmation
    page next to your application's name, so use one they will recognise.
:json state: An opaque value that is returned to you unchanged. Use it to protect against
    cross site request forgery and to identify the user the flow belongs to. It cannot be
    longer than 255 characters.
:json permissions: What ListenBrainz should be able to do with the account: ``import``
    (read listening history, the default), ``listen`` (play music in the ListenBrainz
    player) or ``both``.
:json force: By default, a user who has already granted ListenBrainz the requested
    permissions is sent straight back to your application without seeing the music service
    again. Set this to ``true`` to always show the authorization screen.

We introspect the token, check that it carries the ``listenbrainz:connect-services`` scope
and resolve the ListenBrainz account it belongs to. ListenBrainz user tokens (the ones on
the settings page) are **not** accepted here — connecting a music service on someone's
behalf has to be granted explicitly.

The response contains a single use url:

.. code-block:: json

    {
        "url": "https://listenbrainz.org/connect/spotify/?ticket=...",
        "expires_in": 600
    }

Redirect the user's browser to that url within ``expires_in`` seconds. ListenBrainz shows
them the confirmation page there; once they confirm, it sends them on to the music service
and returns them to your ``redirect_uri`` as described below. The url can only be used once
— it is spent when the user answers the confirmation, either way — and it does **not** log
the user in to ListenBrainz. A url that has expired or has already been used results in a
``400 Bad Request``.

Errors from the POST are returned as JSON with a ``4xx``/``5xx`` status: ``401`` if the
access token is missing, invalid, expired or lacks the scope, ``400`` if the request itself
is malformed and ``503`` if we could not reach the MetaBrainz introspection endpoint.

Returning to your application
-----------------------------

Once the flow finishes, the user is redirected to your ``redirect_uri`` with these query
parameters added:

:query service: The service that was being connected.
:query status: ``connected`` if the account is now connected, ``error`` otherwise.
:query state: The ``state`` you sent, if any.
:query error: Present when ``status`` is ``error``. One of:

    ``invalid_request``
        The music service returned an authorization that we could not match to the request
        that started the flow, or the single use url was opened by a browser logged in to
        a different ListenBrainz account than the one it was created for.
    ``access_denied``
        The user declined — either on the ListenBrainz confirmation page, because the
        account named there was not theirs, or on the music service itself.
    ``email_required``
        The user's MetaBrainz account does not have a verified email address, which
        ListenBrainz requires before connecting a music service. The user has to verify
        their email on their MetaBrainz profile and start the flow again.
    ``expired_request``
        The user took too long to authorize ListenBrainz.
    ``server_error``
        Something went wrong on the ListenBrainz side, or the music service refused the
        authorization for a reason other than the user declining. ``error_description``
        carries the reason the music service gave.

:query error_description: A human readable description of ``error``.

For example, a successful Spotify connection returns the user to:

.. code-block:: none

    https://your.app/listenbrainz/connected?service=spotify&status=connected&state=<your state>

Note that ``status=connected`` tells you the ListenBrainz user connected the service, it
does not tell you which ListenBrainz user that was. If you need to know that, ask the user
for their ListenBrainz user token as you would otherwise.
