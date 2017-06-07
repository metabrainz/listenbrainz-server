messybrainz-server
==================

The server components for the MessyBrainz project.

MessyBrainz is a [MetaBrainz](https://metabrainz.org) project to support unclean metadata. While
[MusicBrainz](https://musicbrainz.org) is designed to link clean metadata to stable identifiers,
there is a need to identify unclean or misspelled data as well. MessyBrainz provides identifiers to
unclean metadata, and where possible, links it to stable MusicBrainz identifiers.

MessyBrainz is currently used in support of two projects, [ListenBrainz](https://listenbrainz.org)
and [AcousticBrainz](https://acousticbrainz.org). Submission to MessyBrainz is restricted, however
the resulting data will be made freely available.

[Website](https://messybrainz.org)

## Installation

You can use [docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/)
to run the MessyBrainz server. Make sure docker and docker-compose are installed.

First, copy `config.py.sample` to `config.py`

Then, in order to download all the software and build and start the containers needed to run
MessyBrainz, run the following command.

    $ ./develop.sh

Now in order to initialize the database (create user, tables etc.) run these commands

    $ docker-compose -f docker/docker-compose.yml -p messybrainz run --rm web bash -c "python3 manage.py init_db"

Everything should be good to go now. You should be able to access the webserver at `http://localhost:8080`.

Also, in order to run the tests, just use the command: `./test.sh`.

## Bug Tracker

MessyBrainz bugs should be reported in the ListenBrainz project of the MetaBrainz bug tracker
[here](https://tickets.metabrainz.org).
