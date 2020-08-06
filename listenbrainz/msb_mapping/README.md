Introduction
============

This sub-project calculates the Messybrainz <=> MusicBrainz mapping. To run it, you'll need a copy of the
musicbrainz database and a copy of the messybrainz database. To create the mapping requires rather a lot of 
RAM. When this software was developed a 64GB server was used.


Installing MessyBrainz data
---------------------------

Get someone from the MB team with DB access to the messybrainz database, make a dump of the DB with pg-dump. Then:

1. `createuser -U musicbrainz -h localhost -p 25432 --pwprompt messybrainz`
2. `createdb -U musicbrainz -O messybrainz -p 25432 -h localhost messybrainz`
3. `psql -U messybrainz -h localhost -p 25432 messybrainz < messybrainz_db.sql`


Install the MessyBrainz mapping code
------------------------------------

To create the actual mapping do:

1. Install and setup musicbrainz-docker ( https://github.com/metabrainz/musicbrainz-docker ). No need for search indexes.
2. Expose the postgres port to the host machine.
3. Copy config.py.sample to config.py and set your DB connect string, based on your setup of musicbrainz-docker.
4. Create a python virtual env (e.g. virtualenv -p python3 .ve) and activate it.
5. Install requirements with `pip install -r requirements.txt`

Then some more DB setup is needed:

`echo "CREATE SCHEMA mapping;" | psql -U musicbrainz -p 5432 -h localhost musicbrainz_db`
`python3 formats.py | psql -U musicbrainz -p 25432 -h localhost musicbrainz_db`

The DB is now setup!


Create the MessyBrainz mapping
------------------------------

You'll create the mapping in two steps:

1. run `./create_recording_pairs.py`
2. run `./create_msid_mapping.py`


Testing and dumping the finished mapping
----------------------------------------

Once these complete, you can run the tests on the mapping:

`./test.sh`

Then you can write the mapping dump files to disk:

`./write_mapping.py`
