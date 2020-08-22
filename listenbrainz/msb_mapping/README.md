Introduction
============

This sub-project calculates the Messybrainz <=> MusicBrainz mapping. To run it, you'll need a copy of the
musicbrainz database and a copy of the messybrainz database. To create the mapping requires rather a lot of
RAM. When this software was developed a 64GB server was used.

The current setup of this code is geared to run on the MetaBrainz infrastructure on the williams server.
The messybrainz-mapper container is a cron job container that does nothing but run the mapping scripts
periodically. See docker/crontab for the current schedule.

To run a mapping do:

```docker exec -it messybrainz-mapper python manage.py create-all```

To test the mapping when it is generated, run:

```docker exec -it messybrainz-mapper python manage.py test-mapping```

To inspect the cron log of the container do:

```docker exec -it messybrainz-mapper python manage.py cron-log```


Algorithm
---------

The mapping is created by selecting all of the single artist releases in MusicBrainz and ordering them
so that most recent digital releases are preferred. The recording name and artist names (artist credit names, really)
for these releases are then matched against the data in MessyBrainz to create this mapping.

The mapping is create in two steps:

Recording Artist Pairs
======================

In this step all of the releases in MusicBrainz are ordered by artist, release type, release date and release format.
The motivation for this step is to give priority to those releases that are likely the source releases that streaming
services (whose listens we're tyring to match with this mapping). It should choose the earliest digital releases of
albums from countries where those albums likely were released first.

After the ordering is complete the recordings from these releases are fetched from the DB and stored in memory.
Only the first occurance of any one pair of artist name - release name is loaded to memory -- all other duplicates
are not loaded into ram and thus not elegible for being part of the mapping.

MSID Mapping
============

The second step involves loading all of the artist-recording pairs into memory and then chunks of the MSB
data. Both are sorted on artist, recording name and then the resultant two sorted lists are walked
comparing data from either lists, quickly finding exact matches of the MSB data to the artist recording pairs.

A secondary step the unmatched MSB recordings will have any data that is in parenthesis removed and the
matching is run again in hopes of finding more matches.

Match Provenance
================

Matches are tagged with a "source" field to make it clear which algorithm produced the match. The two matches
described above are "exact" and "noparen". In the future more matching algorithms will be added -- the goal
here is to let the consumer of the mapping decide which matches are suited for their own purposes. A  task
requiring good matches only may only use the exact matches, where a task with more aggressive goals may
use matches from all sources.


Future improvements
-------------------

This code needs a few more improvements:

1. Add sentry support to give feedback about the status of cron jobs and if something has failed.
2. Add a develop.sh file and documentation on how to use it for local development.
3. Add support for taking generated dump files and moving them to the FTP server
