messybrainz-server
==================

The server components for the MessyBrainz project.

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

