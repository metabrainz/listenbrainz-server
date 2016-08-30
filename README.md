# listenbrainz-server

Server for the ListenBrainz project.

## Installation

*These instructions are meant to get you started quickly with development
process. Installation process in production environment might be different.*

### Prerequisites

In order to install ListenBrainz onto your machine or a VM, you will
need to install:

* Docker engine: https://docs.docker.com/engine/installation/
* Docker compose: https://docs.docker.com/compose/install/


### Configuration file

Copy the file `config.py.sample` to `config.py`:

    $ cp config.py.sample config.py

Next, register for a MusicBrainz application:

   `https://musicbrainz.org/account/applications`

During registration set the callback url to

   `http://<your_host>/login/musicbrainz/post`

Where <your_host> is the DNS name or IP address of the machine running ListenBrainz.

Then set the `MUSICBRAINZ_CLIENT_ID` and `MUSICBRAINZ_CLIENT_SECRET` in
`config.py` to the OAuth Client ID and OAuth Client Secret of your application.


### Build docker containers

    $ docker-compose build

This will automatically download all the needed software and build the necessary
containers needed to run ListenBrainz.

To actually start the containers, do

    $ docker-compose up

This should start the containers and allow you to setup the database.


### Database initialization

To initialize the database (create user, tables, etc.) run these commands:

    $ docker exec -it docker_web_1 python manage.py init_db 
    $ docker exec -it docker_web_1 python manage.py init_msb_db --create-db
    $ docker exec -it docker_influx_writer_1 python admin/influx/create_db.py

After that server should be ready to go. Go to http://localhost:8000 and load the 
ListenBrainz home page.

### Virtual machine

TODO: Finish this

## Documentation

Documentation for the ListenBrainz API is available at [https://listenbrainz.readthedocs.org](https://listenbrainz.readthedocs.org).
You can build the documentation yourself:

    $ cd ~/listenbrainz/docs
    $ make clean html

