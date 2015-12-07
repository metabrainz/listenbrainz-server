# listenbrainz-server

Server for the ListenBrainz project.


## Installation

*These instructions are meant to get you started quickly with development
process. Installation process in production environment might be different.*

First, install [ChefDK](https://downloads.chef.io/chef-dk/), then:

    $ kitchen create    # creates vm for first time
    $ kitchen converge  # provisions/installs from chef cookbooks
    $ kitchen login     # ssh in to vm

### MessyBrainz and ListenStore

ListenStore is our interface to cassandra. It's bundled as part of this
repository, but you must install it so that python can find it.

    $ cd listenstore
    $ python setup.py develop

You can use `setup.py develop` to symlink the ListenStore directory into
site-packages (letting you make changes easily), or use `setup.py install`
to install it.  If you use `setup.py install` and make any changes to
ListenStore you must run install again.

MessyBrainz is an intermediate database to map unknown metadata to stable
UUIDs, and then map these intermediate identifiers to MBIDs
( http://messybrainz.org, https://github.com/metabrainz/messybrainz-server ).

For now you must download and install MessyBrainz separately:

    $ git clone https://github.com/metabrainz/messybrainz-server.git
    $ cd messybrainz-server
    $ pip install -r requirements.txt
    $ python setup.py develop
    $ cp config.py.sample config.py
    $ python manage.py init_db


Future updates will map a local copy of MessyBrainz into the Vagrant
server.

### Python dependencies

Database should be ready. Before running any Python scripts, you need to
install Python dependencies:

    $ cd ~/listenbrainz
    $ pip install -r requirements.txt

### Configuration file

Copy the file `config.py.sample` to `config.py` and edit the postgres
settings. For now you will need to allow your system user to connect
as the postgres admin user with no password.

Register for a MusicBrainz application at
https://musicbrainz.org/account/applications.
During registration set the callback url to
`http://<your_host>/login/musicbrainz/post`.
If you don't change anything during setup, `your_host`
will be `10.1.2.3:8080`

### Database initialization

To initialize the database (create user, tables, etc.) run this command:

    $ python manage.py init_db

After that server should be ready to go.


## Running

To run the *webserver* use this command:

    $ python manage.py runserver

It should be accessible at **http://10.1.2.3:8080/**.

*For information about running listenstore module see /listenstore/README.md
file.*


## Documentation

Documentation for the ListenBrainz API is available at [https://listenbrainz.readthedocs.org](https://listenbrainz.readthedocs.org).
You can build the documentation yourself:

    $ cd docs
    $ make clean html


## Fixing problems

### `LeaderNotAvailableError`

After setting up the server and trying to submit your listens to the server,
this error might appear:

    Kafka listens write error: <class 'kafka.common.LeaderNotAvailableError'>

One way to fix it is to delete all data directories created for Kafka and
Zookeeper.

First, stop both Kafka and Zookeeper services:

    $ sudo service kafka stop
    $ sudo service zookeeper stop

Wipe Kafka's data directory:

    $ sudo rm /var/lib/kafka/kafka-logs/*

and Zookeeper's:

    $ sudo rm /var/lib/zookeeper/*

Start them again:

    $ sudo service kafka start
    $ sudo service zookeeper start

Finally, create a `listens` topic in Kafka:

    $ sudo /opt/kafka/bin/kafka-topics.sh --create --zookeeper localhost:2181 --topic "listens" --partitions 1 --replication-factor 1

This should fix the issue. See this page for more info about described method:
https://stackoverflow.com/a/24028480
