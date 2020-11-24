Introduction
============

This project provides three related components:

1. Artist credit recording mapping which chooses the earliest digital releases from MusicBrainz and then creates
a table with the first instance of any (artist_credit, recording_name) and maps it to the MBIDs from which it
originated. This index is useful for resolving ListenBrainz listens where we may only have an artist name and
a recording name onto sane MusicBrainz release that would be a reasonable choice for what users might expect.

2. The same mapping as above, but focused on having the very first release of any given (artist_credit, recording_name)
so that it can be used to find the first release year of that pair.

3. A typesense index that takes the data from #1 and generates an index that can be used to quickly and fuzzily
look up data from the table in #1. This index will serve as the official "MusicBrainz mapping".



```docker exec -it messybrainz-mapper python manage.py create-all```

To test the mapping when it is generated, run:

```docker exec -it messybrainz-mapper python manage.py test-mapping```

To inspect the cron log of the container do:

```docker exec -it messybrainz-mapper python manage.py cron-log```

To run a dev container and do connect it to a musicbrainz-docker instance, do:

```
docker build -f Dockerfile.dev -t metabrainz/mbid-mapper .
docker run --rm -it --network musicbrainzdocker_default metabrainz/mbid-mapping python3 manage.py create-all
docker run -p 8108:8108 -d -v /home/robert/typesense:/data --name=typesense --network=musicbrainzdocker_default typesense/typesense:0.17.0 --data-dir /data --api-key=root-api-key
```

Recording Artist Pairs
======================

In this step all of the releases in MusicBrainz are ordered by artist, release type, release date and release format.
The motivation for this step is to give priority to those releases that are likely the source releases that streaming
services (whose listens we're tyring to match with this mapping). It should choose the earliest digital releases of
albums from countries where those albums likely were released first.

After the ordering is complete the recordings from these releases are fetched from the DB and stored in memory.
Only the first occurance of any one pair of artist name - release name is loaded to memory -- all other duplicates
are not loaded into ram and thus not elegible for being part of the mapping.
