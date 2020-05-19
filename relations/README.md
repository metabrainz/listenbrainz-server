Introduction
============

How artists and artist_credits relate to each other can be derived by loading various
artist albums in MusicBrainz and using the fact that two artists(_credits) appear on 
the same album as a fact that they are somewhat related. 

Given this principle, these scripts require a MusicBrainz replicated slave instance
and will create a new schema "relations" inside the MusicBrainz database. The create
scripts will calculate the relationships, create new tables and then build indexes
on those tables.

Installation
------------

To build the artist-artist and artist_credit-artist_credit relations, you'll need to:

1. Install and setup musicbrainz-docker ( https://github.com/metabrainz/musicbrainz-docker ). No need for search indexes.
2. Expose the postgres port to the host machine.
3. Copy config.py.sample to config.py and set your DB connect string, based on your setup of musicbrainz-docker.
4. Create a python virtual env (e.g. virtualenv -p python3 .ve) and activate it.
5. Install requirements with `pip install -r requirements.txt`
6. run create_artist_relations.py and.or create_artist_credit_relations.py to actually create the relationships.
7. run write_artist_relations.py to save the relation to a dump file.
