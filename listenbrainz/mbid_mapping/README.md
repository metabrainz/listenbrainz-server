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

Creating mappings and running tests
-----------------------------------

You will need to have a copy of [musicbrainz-docker](https://github.com/metabrainz/musicbrainz-docker)
installed and running in order to run these commands.


To build the docker image for the mapping tools:

```
cp config.py.sample config.py
./build.sh
```

config.py may need tweaking, depending on your setup. Then to access the manage.py command that is used to
invoke the various functions, do:

```docker run --rm -it --network musicbrainz-docker_default metabrainz/mbid-mapping python3 manage.py```

To create the MusicBrainz MBID mapping run:

```manage.py mbid-mapping```

To create the MusicBrainz year mapping run:

```manage.py year-mapping```


Creating a typesense index for searching the mapping
----------------------------------------------------

If you plan to create a typesense index, you'll need typesense installed. First set an API KEY in config.py,
then run:

```
docker run -p 8108:8108 -d -v listenbrainz-typesense:/data --name=listenbrainz-typesense --network=musicbrainz-docker_default typesense/typesense:0.19.0 --data-dir /data --api-key=<the api key>
```

To create the typesense index:

```manage.py build-index```

To test searching the index:

```manage.py search sun shines tv```

To run the mapping tests:

```manage.py test-mapping```
