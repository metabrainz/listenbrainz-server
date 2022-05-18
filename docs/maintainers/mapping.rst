MBID Mapping
============

For a background on how the mapping works, see :ref:`developers-mapping`


Containers
^^^^^^^^^^

The mapping tools run in two containers:

 * ``mbid-mapping-writer-prod``: Populates the ``mbid_mapping`` table for new listens. Built from the 
    main ListenBrainz dockerfile.

 * ``mbid-mapping``: Periodically generates the MBID Mapping supplemental tables, typesense index,
    and huesound index. Built from ``listenbrainz/mbid_mapping/Dockerfile``


Data sources
^^^^^^^^^^^^

In the production environment, the ``mbid-mapping`` container reads from the MB replica on aretha.


Debugging lookups
^^^^^^^^^^^^^^^^^

If a listen isn't showing up as mapped on ListenBrainz, one of the following might be true:

* The item wasn't in musicbrainz at the time that the lookup was made
* There is a bug in the mapping algorithm

If the recording doesn't exist in MusicBrainz during mapping, a row will be added to the ``mbid_mapping`` table
with the MSID and a ``match_type`` of ``no_match``. Currently no_match values aren't looked up again automatically.

You can test the results of a lookup by using `https://labs.api.listenbrainz.org/explain-mbid-mapping <https://labs.api.listenbrainz.org/explain-mbid-mapping>`
This uses the same lookup process that the mapper uses. If this returns a result, but there is no mapping present
it could be due to data being recently added to MusicBrainz or improvements to the mapping algorithm.

If no data is returned or an incorrect match is being returned, this should be reported to us, by adding a comment
to `LB-1036 <https://tickets.metabrainz.org/browse/LB-1036>`.

In this case you can retrigger a lookup by seting the ``mbid_mapping.last_updated`` field to '1970-01-01 00:00:00' (the unix epoch). 
The mapper will pick up these items and put them on the queue again.

.. code:: sql

    UPDATE mbid_mapping SET last_updated = 'epoch' WHERE recording_msid = '00000737-3a59-4499-b30a-31fe2464555d';
    UPDATE mbid_mapping SET last_updated = 'epoch' WHERE match_type = 'no_match' AND last_updated = now() - interval '1 day';

In the LB production environment these items will be picked up and re-processed once a day.
