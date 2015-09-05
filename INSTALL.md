Installing MessyBrainz Server
==============================

Prerequisites
-------------

* [Python](https://www.python.org/) 2.7.x
* [PostgreSQL](http://www.postgresql.org/) >=9.2 (needs the JSON data type)
* [memcached](http://memcached.org/)

For example in the latest Ubuntu, this command will install pre-requisites:

    $ sudo apt-get install python-dev python-virtualenv memcached \
        postgresql-9.3 postgresql-client-9.3 postgresql-server-dev-9.3


Web Server
----------

It is recommended, although optional, to first set up a virtual environment and
activate it:

    $ virtualenv venv
    $ . ./venv/bin/activate

### Python dependencies

Then use `pip` to install the required Python dependencies:

    $ pip install -r requirements.txt

### Configuration

Copy over `config.py.sample` to `config.py` and edit its content to fit your
environment.

### Creating the database

After you tweak configuration file, database needs to be created:

    $ python manage.py init_db

*Optional:* You might want to create a database that will be used by tests:

    $ python manage.py init_test_db

### Starting the server

After all this, you can run the site/server using `./server.py`.
Use `./server.py -h` to get a list of command-line switches
to further suit your local environment (e.g., port, listening address, ...).
