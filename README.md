# listenbrainz-server

Server for the ListenBrainz project.

[Website](https://listenbrainz.org) | [Beta website](https://beta.listenbrainz.org) | [Bug tracker](https://tickets.metabrainz.org/projects/LB/issues)

## Installation

*These instructions are meant to get you started quickly with development
process. Installation process in production environment might be different.*

### Prerequisites

In order to install ListenBrainz onto your machine or a VM, you will
need to install:

* Docker engine: https://docs.docker.com/engine/installation/
* Docker compose: https://docs.docker.com/compose/install/


### Configuration file

Copy the file `listenbrainz/config.py.sample` to `listenbrainz/config.py`:

    $ cp listenbrainz/config.py.sample listenbrainz/config.py

Next, register for a MusicBrainz application:

   `https://musicbrainz.org/account/applications`

During registration set the callback url to

   `http://<your_host>/login/musicbrainz/post`

Where <your_host> is the DNS name or IP address of the machine running ListenBrainz.
An example callback url if you're running the server on your own local machine would
be

    `http://localhost/login/musicbrainz/post`

Then set the `MUSICBRAINZ_CLIENT_ID` and `MUSICBRAINZ_CLIENT_SECRET` in
`config.py` to the OAuth Client ID and OAuth Client Secret of your application.


### Start the services

    $ ./develop.sh

This will automatically download all the needed software and build and start the necessary
containers needed to run ListenBrainz.

### Database initialization

To initialize the database (create user, tables, etc.) run these commands:

    $ docker-compose -f docker/docker-compose.yml -p listenbrainz run --rm web python3 manage.py init_db --create-db
    $ docker-compose -f docker/docker-compose.yml -p listenbrainz run --rm web python3 manage.py init_msb_db --create-db
    $ docker-compose -f docker/docker-compose.yml -p listenbrainz run --rm web python3 manage.py init_influx


After that server should be ready to go. Go to http://localhost and load the
ListenBrainz home page.

### Running tests

In order to run the unit tests for ListenBrainz, simply run:

    $ ./test.sh

This will build and run the containers needed to run the tests. Each of these containers will not use volumes
that link to data outside of the containers and thus will not interfere with production databases.

Also, run the integrations tests for ListenBrainz using the following command:

    $ ./integration-test.sh

### Calculating statistics

ListenBrainz uses Google BigQuery to calculate statistics. You need to add a BigQuery credentials file
called `bigquery-credentials.json` to the `credentials` directory for this to work. This file can be
obtained from the Google BigQuery site by creating a new project. The `WRITE_TO_BIGQUERY` variable in
`config.py` needs to be set to True also.

The stats are automatically calculated in the `scheduler` container, but if you want to manually
start the stats calculation, run the following command.

    $ docker-compose -f docker/docker-compose.yml -p listenbrainz run --rm web python manage.py stats calculate

## Documentation

Documentation for the ListenBrainz API is available at [https://listenbrainz.readthedocs.org](https://listenbrainz.readthedocs.org).
You can build the documentation yourself:

    $ cd ~/listenbrainz/docs
    $ make clean html

## License Notice

```
listenbrainz-server - Server for the ListenBrainz project.

Copyright (C) 2017 MetaBrainz Foundation Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
```
