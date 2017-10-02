Setting up a development environment
====================================

To contribute to the ListenBrainz project, you need a development environment. With your
development environment, you can test your changes before submitting a patch back to the project.
This guide helps you set up a development environment and run ListenBrainz locally on your
workstation. By the end of this guide, you will have…

* Install system dependencies
* Register a MusicBrainz application
* Initialize development databases
* Run ListenBrainz locally on your workstation


Install dependencies
--------------------

The ``listenbrainz-server`` is shipped in Docker containers. This helps create your development
environment and later deploy the application. Therefore, to work on the project, you need to
install Docker and use containers for building the project. Containers save you from installing all
of this on your own workstation.

See the different installation instructions for your distribution below.

CentOS / RHEL
^^^^^^^^^^^^^

.. code-block:: bash

    sudo yum install epel-release
    sudo yum install docker docker-compose

Debian / Debian-based systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    sudo apt-get update && sudo apt-get install docker docker-compose

Fedora
^^^^^^

.. code-block:: bash

    sudo dnf install docker docker-compose

openSUSE
^^^^^^^^

.. code-block:: bash

    sudo zypper install docker docker-compose

Ubuntu / Ubuntu-based systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    sudo apt-get update && sudo apt-get install docker docker-compose


Register a MusicBrainz application
----------------------------------

Next, you need to register your application and get a OAuth token from MusicBrainz. Using the OAuth
token lets you sign into your development environment with your MusicBrainz account. Then, you can
import your plays from somewhere else.

To register, visit the `MusicBrainz applications page`_. There, look for the option to `register`_
your application. Fill out the form with these three options.

* **Name**: (any name you want and will recognize, I used ``listenbrainz-server-devel``)
* **Type**: ``Web Application``
* **Callback URL**: ``http://localhost:8000/login/musicbrainz/post``

After entering this information, you'll have a OAuth client ID and OAuth client secret. You'll use
these for configuring ListenBrainz.

Update config.py
^^^^^^^^^^^^^^^^

With your new client ID and secret, update the ListenBrainz configuration file. If this is your
first time configuring ListenBrainz, copy the sample to a live configuration.

.. code-block:: bash

    cp listenbrainz/config.py.sample listenbrainz/config.py


Next, open the file with your favorite text editor and look for this section.

.. code-block:: yaml

    # MusicBrainz OAuth
    MUSICBRAINZ_CLIENT_ID = "CLIENT_ID"
    MUSICBRAINZ_CLIENT_SECRET = "CLIENT_SECRET"


Update the strings with your client ID and secret. After doing this, your ListenBrainz development
environment is able to authenticate and log in from your MusicBrainz login.


Initialize ListenBrainz databases
---------------------------------

Your development environment needs some databases present to work. Before proceeding, run these
three commands to initialize the databases.

.. code-block:: bash

    docker-compose -f docker/docker-compose.yml -p listenbrainz run --rm web python3 manage.py init_db --create-db
    docker-compose -f docker/docker-compose.yml -p listenbrainz run --rm web python3 manage.py init_msb_db --create-db
    docker-compose -f docker/docker-compose.yml -p listenbrainz run --rm web python3 manage.py init_influx


Your development environment is now ready. Now, let's actually see ListenBrainz load locally!


Run the magic script
--------------------

Once you have done this, run the ``develop.sh`` script in the root of the repository. Using
``docker-compose``, the script creates multiple Docker containers for the different services and
parts of the ListenBrainz server. Running this script will start Redis, PostgreSQL, InfluxDB, and
web server containers, to name a few. But this also makes it easy to stop them all later.

.. code-block:: bash

    ./develop.sh


You will see the containers build and eventually run. Leave the script running to see your
development environment. Later, you can shut it down by pressing CTRL^C. Once everything is
running, visit your new site from your browser!

.. code-block:: none

    http://localhost:8000/


Now, you are all set to begin making changes and testing them in your development environment!

.. _MusicBrainz applications page: https://musicbrainz.org/account/applications
.. _register: https://musicbrainz.org/account/applications/register
