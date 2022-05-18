:orphan:

.. _developers-mapping:

MBID Mapping
============

The MBID mapping scripts allow us to take metadata from the messybrainz database and look up recording MBIDs
from the MusicBrainz database.

.. note::
    The MBID Mapping source code lives in ``listenbrainz/mbid_mapping`` but is run independently
    from the main listenbrainz web docker image. You can use your own virtual environment or use
    ``listenbrainz/mbid_mapping/build.sh`` to build a standalone docker image.

Database tables
^^^^^^^^^^^^^^^

The MBID Mapping supplemental tables hold preprocessed data from the MusicBrainz database.

* ``mapping.canonical_musicbrainz_data``: The MBID and Name of Recordings, Artists (and credits), and Releases for all recordings in MusicBrainz
* ``mapping.canonical_recording_redirect``: A mapping to find the "canonical" recording given an artist credit + recording name
* ``mapping.canonical_release_redirect``: A mapping to find the "canonical" release given an artist credit + release name

These tables can be populated by running 

.. code:: bash

    python mapper/manage.py canonical-data

The update process build the new data in a temporary table and then
replaces them in a single transaction. This means that lookups can continue to run on the 
existing tables while the new ones are being built.

Fuzzy lookups
^^^^^^^^^^^^^

We use typesense as a way of performing quick, fuzzy lookups based on artist name and recording name

Build the typesese index with

.. code:: bash

    python mapper/manage.py build-index

As with the data tables, a new typesense collection is created and then swapped into place in a
single operation.

Build the mapping tables and then the typesense index directly afterwards with 

.. code:: bash

    python mapper/manage.py create-all

MBID Mapper
^^^^^^^^^^^

The mapper looks for new MSIDs submitted to messybrainz and finds a matching MBID in MusicBrainz

    ``python3 -u -m listenbrainz.mbid_mapping_writer.mbid_mapping_writer``

A background thread pushes items to be processed onto a queue - recent submissions first, and then if nothing
is to be done, old items.
The processing thread pops items off the queue and then looks them up, adding them to the ``mbid_mapping`` table.

There is also a background thread that fires off daily, which looks for listens that have been written to the 
listens table, but for some reason do not have a matching mapping entry. (This could happen due to 
restarts or problems with the mapper itself). These are called legacy listens.

The background thread will walk the entire listens table once a day to find these legacy listens and attempt to
map them. In the same thread we also look for mapping items with timestamp of the unix epoch (1970-01-01 00:00:00),
which indicates that they ought to be re-checked. Currently we have no automated mechanism in place for setting any mapping 
entries to the epoch.

TODO: Detuning algorithm
TODO: match quality types
