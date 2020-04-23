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

MessyBrainz uses the MusicBrainz database for certain functionalities. Hence, it is necessary
to set up the MusicBrainz database first.

You can import the database dumps by downloading and importing the data in
a single command:

    $ docker-compose -f docker/docker-compose.yml -p messybrainz run musicbrainz_db

**Note**

You can also manually download the dumps and then import them:-

1. For this, you have to download the dumps ``mbdump.tar.bz2`` and ``mbdump-derived.tar.bz2``
from http://ftp.musicbrainz.org/pub/musicbrainz/data/fullexport/.

**Warning**: Make sure to get the latest dumps

2. Then the environment variable ``DUMPS_DIR`` must be set to the path of the
folders containing the dumps. This can be done by:

```
$ export DUMPS_DIR="Path of the folder containing the dumps"
```

You can check that the variable ``DUMPS_DIR`` has been succesfully assigned or not by:

```
$ echo $DUMPS_DIR
```

This must display the path of your folder containing the database dumps. The folder must contain at least the file    ``mbdump.tar.bz2``.

3. Then import the database dumps by this command:

```
$ docker-compose -f docker/docker-compose.yml run -v $DUMPS_DIR:/home/musicbrainz/dumps \
     -v $PWD/data/mbdata:/var/lib/postgresql/data/pgdata musicbrainz_db
```

**Note**

You can also use the smaller sample dumps available at http://ftp.musicbrainz.org/pub/musicbrainz/data/sample/
to set up the MusicBrainz database. However, note that these dumps are .tar.xz
dumps while MessyBrainz currently only supports import of .tar.bz2 dumps.
So, a decompression of the sample dumps and recompression into .tar.bz2 dumps
will be needed. This can be done using the following command:

    xzcat mbdump-sample.tar.xz | bzip2 > mbdump.tar.bz2

**Warning**

Keep in mind that this process is very time consuming, so make sure that you don't delete the ``data/mbdata`` directory accidently. Also make sure that you have about 25GB of free space to keep the MusicBrainz data.


Now in order to initialize the database (create user, tables etc.) run these commands

    $ docker-compose -f docker/docker-compose.yml -p messybrainz run --rm web bash -c "python3 manage.py init_db"

Then, in order to download all the software and build and start the containers needed to run
MessyBrainz, run the following command.

    $ ./develop.sh

Everything should be good to go now. You should be able to access the webserver at `http://localhost:8080`.

If you want to make configuration changes, first copy `custom_config.py.sample` to `custom_config.py`
and then make your config changes in the `custom_config.py` file.

Also, in order to run the tests, just use the command: `./test.sh`.

## Bug Tracker

MessyBrainz bugs should be reported in the ListenBrainz project of the MetaBrainz bug tracker
[here](https://tickets.metabrainz.org).
