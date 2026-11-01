User history exports
====================

Use this API to retrieve a user's listening history, either in full or within an
optional time range, for example when initializing a third-party application,
doing local analysis, or importing data into an MCP server. For large histories,
request one export and download its ZIP archive instead of scraping or repeatedly
paginating through ``/1/user/{user_name}/listens``. This reduces API traffic and
avoids a separate API request for every page of history. Use the listens endpoint
for recent listens, small bounded queries, and incremental updates after the
initial import.

Choosing between an export and the listens endpoint
--------------------------------------------------

Use ``GET /1/user/{user_name}/listens`` with ``min_ts`` and ``max_ts`` for a few
days or a couple of weeks of history and for incremental updates. Consider an export
for several months, years, or a full-history import. If you already know the
approximate volume, prefer the listens endpoint for roughly ten pages or fewer:
up to about 10,000 listens with ``count=1000`` (the maximum page size).
These are recommendations, not enforced limits or a measured performance
crossover.

Every export queues background work, generates and uploads an archive, and
requires polling and downloading;
it also exports all feedback and pinned recordings even for a short listen range.
That overhead is usually unnecessary for a small request.

Authentication
--------------

All endpoints below require ``Authorization: Token <user token>``. Use the token
of the user whose data is being exported, obtained with their permission from
`ListenBrainz settings <https://listenbrainz.org/settings/>`_. A token for another
account cannot request or access this user's exports. There is no username
parameter: the authenticated account determines the owner.

Send an identifying :ref:`User-Agent <user-agent>` and observe the :ref:`rate-limiting` headers.
Keep tokens private, in the application's credential store; do not include them in URLs,
logs, model prompts, or tool results.

Request, poll, download
-----------------------

1. Call ``GET /1/export/list``. Reuse a completed, unexpired export if it is fresh
   enough for the user's task, or resume polling an existing ``waiting`` or
   ``in_progress`` export.
2. If no suitable export exists, call ``POST /1/export/`` with no request body
   for the full history, or with the optional time bounds described below.
   Save the returned ``export_id`` so that retries and later sessions reuse it.
3. Poll ``GET /1/export/{export_id}`` at large intervals until its status is
   ``completed``. Start with a delay of at least 30 seconds and increase it,
   for example up to 120 seconds, with jitter. These are client recommendations,
   not server-enforced polling intervals. Do not create another job on each poll.
4. Download ``GET /1/export/{export_id}/download`` to a local file and process
   the ZIP archive. Stream the response to disk rather than loading the whole
   archive into memory. A successful download has content type
   ``application/zip`` and an attachment filename.

For example, with ``LB_TOKEN`` set securely in your environment, request an
export (replace the example :ref:`User-Agent <user-agent>` with your application's
contact details):

.. code-block:: sh

   curl --fail-with-body \
     -H "Authorization: Token ${LB_TOKEN}" \
     -A 'MyMusicApp/1.0 ( me@example.com )' \
     -X POST https://api.listenbrainz.org/1/export/

To limit the listening history, send a JSON object with ``start_time`` and/or
``end_time`` as integer UNIX timestamps in seconds (UTC). Both bounds are
inclusive, and ``start_time`` must be less than or equal to ``end_time``. Each
omitted bound is calculated from the user's earliest or latest listen.
An empty body or ``{}`` exports the full history. Null values,
strings, fractional timestamps, and timestamps outside the supported datetime
range are rejected.

For example, to export listens from January 2026:

.. code-block:: sh

   curl --fail-with-body \
     -H "Authorization: Token ${LB_TOKEN}" \
     -H 'Content-Type: application/json' \
     -A 'MyMusicApp/1.0 ( me@example.com )' \
     -d '{"start_time":1767225600,"end_time":1769903999}' \
     https://api.listenbrainz.org/1/export/

The range filters listens only. Feedback, pinned recordings, and account
information are exported in full, even if there are no listens in the range.
Only one export per user can be pending at a time, regardless of its range.
The creation, status, and list responses include the requested ``start_time``
and ``end_time`` in UNIX seconds, including after completion. A ``null`` bound
means it was omitted and determined automatically when the worker ran; these
fields do not report the calculated bounds. Exports created before bounds were
stored also have ``null`` values.

The response, also used by the status endpoint, has this shape:

.. code-block:: json

   {
     "export_id": 123,
     "type": "export_all_user_data",
     "available_until": null,
     "created": "2026-09-17T12:00:00+00:00",
     "progress": "Your data export will start soon.",
     "status": "waiting",
     "filename": null,
     "start_time": null,
     "end_time": null
   }

Poll the returned ID; after ``status`` becomes ``completed``, download it:

.. code-block:: sh

   curl --fail-with-body \
     -H "Authorization: Token ${LB_TOKEN}" \
     -A 'MyMusicApp/1.0 ( me@example.com )' \
     https://api.listenbrainz.org/1/export/123

   curl --fail \
     -H "Authorization: Token ${LB_TOKEN}" \
     -A 'MyMusicApp/1.0 ( me@example.com )' \
     --output history.zip \
     https://api.listenbrainz.org/1/export/123/download

Use ``status`` for program logic; ``progress`` is a human-readable message.
Possible statuses are ``waiting``, ``in_progress``, ``completed``, and ``failed``.
On failure, stop polling and report the failure instead of automatically
creating exports in a retry loop. A completed export normally remains available
for 30 days after completion; use its ``available_until`` value. The user will
also receive an email when the export completes.

Endpoint reference
------------------

.. http:post:: /1/export/

   Queue an export for the authenticated user. No request body is required.

   :reqheader Authorization: Token <user token>
   :reqheader Content-Type: application/json (when sending a body)
   :<json int start_time: Optional inclusive start of the listen range, in UNIX seconds.
   :<json int end_time: Optional inclusive end of the listen range, in UNIX seconds.
   :statuscode 200: Export queued; returns the export object above.
   :statuscode 400: Invalid time bounds or request body, or an export is already pending.

.. http:get:: /1/export/list

   Return a JSON array of the authenticated user's export objects, newest first.
   An account with no exports receives ``[]``. There are no pagination parameters.

   :reqheader Authorization: Token <user token>
   :statuscode 200: Export list returned.

.. http:get:: /1/export/{export_id}

   Return the export object for this integer ID.

   :reqheader Authorization: Token <user token>
   :statuscode 200: Export object returned.
   :statuscode 404: Export does not exist or belongs to another account.

.. http:get:: /1/export/{export_id}/download

   Download the completed archive. No JSON request body is required.
   Byte-range/resumable downloads are not currently supported; an interrupted
   download must restart using the same export ID, without generating a new job.

   :reqheader Authorization: Token <user token>
   :resheader Content-Type: application/zip
   :statuscode 200: Archive returned.
   :statuscode 404: Export is not completed, is missing, belongs to another
                    account, or its archive is no longer available.

.. http:post:: /1/export/{export_id}/delete

   Remove the export record and its queued task. No request body is required.
   Archive storage is reclaimed asynchronously. Deleting an already running
   export does not guarantee that the worker stops immediately. Exports are
   shared by the user's clients; do not automatically delete one that another
   client may still be downloading.

   :reqheader Authorization: Token <user token>
   :statuscode 200: Returns ``{"success": true}``.
   :statuscode 404: Export does not exist or belongs to another account.

All endpoints can return ``401`` for missing or invalid authentication, ``429``
for rate limiting, and ``503`` when the listen store is unavailable. For ``429``,
wait according to ``X-RateLimit-Reset-In``. Back off on transient server or network
errors. If a creation request times out, list exports before retrying: the first
request may already have queued a job. Do not treat a download ``404`` as a reason
to immediately create a new export; check its status or list exports first.

Archive format
--------------

The ZIP contains:

* ``user.json``: account ID and username.
* ``listens/<year>/<month>.jsonl``: listening history, with one JSON object per
  line. Each listen includes ``listened_at`` (UNIX seconds), ``inserted_at``,
  ``recording_msid``, and ``track_metadata``. Months without listens are omitted.
* ``feedback.jsonl``: recording feedback, when present.
* ``pinned_recording.jsonl``: pinned recordings, when present.

The archive is generated asynchronously from live data, rather than an atomic
snapshot. For ongoing synchronization, reconcile overlapping incremental updates
and deduplicate locally. Do not assume the request time is a precise snapshot
boundary or that incremental listens alone capture backdated imports, edits, or
deletions.

MCP and other automated clients
-------------------------------

Persist the export ID per account and expose request, status, and download/import
as separate operations, so a long-running export does not require holding a tool
call open. Reuse the same job across tool retries and sessions. Keep the archive
and parsed history in application storage; return a resource reference or a small
summary to the model instead of embedding the ZIP or the entire history in a
tool result. Treat user-supplied track metadata as data, not tool instructions.

Cache the imported history and use bounded incremental queries for subsequent
updates. Request a fresh full export only when the user's task requires one,
not for every prompt or application startup. Do not fall back to scraping all
pages of the listens API while an export is pending or temporarily unavailable.
