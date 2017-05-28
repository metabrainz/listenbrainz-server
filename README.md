messybrainz-server
==================

The server components for the MessyBrainz project.

## Installation

### Vagrant VM

The easiest way to start is to setup ready-to-use [Vagrant](https://www.vagrantup.com/)
VM. To do that [download](https://www.vagrantup.com/downloads.html) and install
Vagrant for your OS. Then copy two config files:

1. `config.py.sample` to `config.py` *(you don't need to modify this file)*

After that you can spin up the VM and start working with it:

    $ vagrant up

There are some environment variables that you can set to affect the
provisioning of the virtual machine.

 * `AB_NCPUS`: Number of CPUs to put in the VM (default 1)
 * `AB_MEM`:   Amount of memory (default 1024mb)
 * `AB_MIRROR`: ubuntu mirror (default archive.ubuntu.com)

You can start the web server (will be available at http://127.0.0.1:8080/):

    $ vagrant ssh
    $ cd messybrainz-server
    $ python manage.py runserver

There are some shortcuts defined using fabric to perform commonly used
commands:

 * `fab vpsql`: Load a psql session. Requires a local psql client
 * `fab vssh`: Connect to the VM more efficiently, saving the settings
               so that you don't need to run vagrant each time you ssh.

### Docker

You can use [docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/)
to run the MessyBrainz server. Make sure docker and docker-compose are installed.

First, copy `config.py.sample` to `config.py`

Then, in order to download all the software and build and start the containers needed to run
MessyBrainz, run the following command.

    $ ./develop.sh

Now in order to initialize the database (create user, tables etc.) run these commands

    $ docker-compose -f docker/docker-compose.yml -p messybrainz run --rm web bash -c "python manage.py init_db"

Everything should be good to go now. You should be able to access the webserver at `http://localhost:8080`.

Also, in order to run the tests, just use the command: `./test.sh`.

### The Usual Way

Full installation instructions are available in [INSTALL.md](https://github.com/metabrainz/messybrainz-server/blob/master/INSTALL.md) file.
