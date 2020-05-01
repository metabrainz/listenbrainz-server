Set up ListenBrainz Server development environment
==================================================

To contribute to the ListenBrainz project, you need a development environment.
With your development environment, you can test your changes before submitting a
patch to the project. This guide helps you set up a development environment
and run ListenBrainz locally on your workstation. By the end of this guide, you
will have…

* Installed system dependencies
* Registered a MusicBrainz application
* Initialized development databases
* Running ListenBrainz Server


Install dependencies
--------------------

The ``listenbrainz-server`` is shipped in Docker containers. This helps create
your development environment and later deploy the application. Therefore, to
work on the project, you need to install Docker and use containers for building
the project. Containers save you from installing all of this on your own
workstation.

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

Next, you need to register your application and get an OAuth token from
MusicBrainz. Using the OAuth token lets you sign into your development
environment with your MusicBrainz account. Then, you can import your plays from
somewhere else.

To register, visit the `MusicBrainz applications page`_. There, look for the
option to `register`_ your application. Fill out the form with these three
options.

- **Name**: (any name you want and will recognize, e.g.
  ``listenbrainz-server-devel``)

- **Type**: ``Web Application``

- **Callback URL**: ``http://localhost/login/musicbrainz/post``

After entering this information, you'll have an OAuth client ID and OAuth client
secret. You'll use these for configuring ListenBrainz.


.. _MusicBrainz applications page: https://musicbrainz.org/account/applications
.. _register: https://musicbrainz.org/account/applications/register


Update config.py
^^^^^^^^^^^^^^^^

With your new client ID and secret, update the ListenBrainz configuration file.
If this is your first time configuring ListenBrainz, copy the sample to a live
configuration.

.. code-block:: bash

    cp listenbrainz/config.py.sample listenbrainz/config.py

Next, open the file with your favorite text editor and look for this section.

.. code-block:: yaml

    # MusicBrainz OAuth
    MUSICBRAINZ_CLIENT_ID = "CLIENT_ID"
    MUSICBRAINZ_CLIENT_SECRET = "CLIENT_SECRET"

Update the strings with your client ID and secret. After doing this, your
ListenBrainz development environment is able to authenticate and log in from
your MusicBrainz login.

Also, in order for the Last.FM import to work, you should also update your
Last.FM API key in this file. Look for the following section in the file.

.. code-block:: yaml

    # Lastfm API
    LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
    LASTFM_API_KEY = "USE_LASTFM_API_KEY"

Update the Last.FM API key with your key. After doing this, your
ListenBrainz development environment is able to import your listens from Last.FM.

In case you don't have a Last.FM API key, you can get it from `Last.FM API page`_.

You also need to update the ``API_URL`` field value to ``http://localhost``.

We also have a Spotify importer script which imports listens from
Spotify automatically using the Spotify API. In order to run this in your
local development environment, you'll have to register an application on the
`Spotify Developer Dashboard`_. Use ``http://localhost/profile/connect-spotify/callback``
as the callback URL.

After that, fill out the Spotify client ID and client secret in the following
section of the file.

.. code-block:: yaml

    # SPOTIFY
    SPOTIFY_CLIENT_ID = ''
    SPOTIFY_CLIENT_SECRET = ''

.. note::

    The hostname on the callback URL must be the same as the host you use to
    access your development server. If you use something other than ``localhost``, you
    should update the ``SPOTIFY_CALLBACK_URL`` field accordingly.

.. _Last.FM API page: https://last.fm/api

.. _Spotify Developer Dashboard: https://developer.spotify.com/dashboard/applications


Initialize ListenBrainz containers
----------------------------------

Next, run ``develop.sh build`` in the root of the repository. Using
``docker-compose``, it creates multiple Docker containers for the different
services and parts of the ListenBrainz server. This script starts Redis,
PostgreSQL, InfluxDB, and web server containers. This also makes it easy to stop
them all later.

The first time you run it, it downloads and creates the containers. But it's not
finished yet.

.. code-block:: bash

    ./develop.sh build


Initialize ListenBrainz databases
---------------------------------

Your development environment needs some specific databases to work. Before
proceeding, run these three commands to initialize the databases.

.. code-block:: bash

    ./develop.sh manage init_db --create-db
    ./develop.sh manage init_msb_db --create-db
    ./develop.sh manage init_influx

Your development environment is now ready. Now, let's actually see ListenBrainz
load locally!


Install node dependencies
-------------------------

You also need to install some JavaScript dependencies.

.. code-block:: bash

    ./develop.sh npm


Run the magic script
--------------------

Now that the databases are initialized, always start your development
environment by executing ``develop.sh up``. Now, it will work as
expected.

.. code-block:: bash

    ./develop.sh up

You will see the containers eventually run again. Leave the script running to
see your development environment in the browser. Later, shut it down by pressing
CTRL^C. Once everything is running, visit your new site from your browser!

.. code-block:: none

   http://localhost

Now, you are all set to begin making changes and seeing them in real-time inside
of your development environment!

Once you are done with your work, shut down the containers using the following command. 

.. code-block:: bash

    ./develop.sh down

Using develop.sh
----------------
We provide a utility to wrap docker compose and some common development processes.

To open a psql session, run:

.. code-block:: bash

    ./develop.sh psql

To pass any docker-compose command, run:

.. code-block:: bash

    ./develop.sh <command>

To get a list of valid docker-compose commands, run:

.. code-block:: bash

    ./develop.sh help

``develop.sh`` provides a direct interface to invoke manage.py.
To invoke manage.py, run:

.. code-block:: bash

    ./develop.sh manage <command>

To get a list of manage.py commands, run:

.. code-block:: bash

    ./develop.sh manage --help

Test your changes with unit tests
---------------------------------
								
Unit tests are an important part of ListenBrainz. It helps make it easier for
developers to test changes and help prevent easily avoidable mistakes later on.
Before committing new code or making a pull request, run the unit tests on your
code.

.. code-block:: bash

   ./test.sh

This builds and runs the containers needed for the tests. This script configures
test-specific data volumes so that test data is isolated from your development
data.

To run tests faster, you can use some options to start up the test infrastructure
once so that subsequent running of the tests is faster:

.. code-block:: bash

   ./test.sh -u # start up and initialise the database
   ./test.sh    # run tests, do this as often as you need to
   ./test.sh -s # stop test containers, but don't remove them
   ./test.sh -d # stop and remove all test containers

If you made any changes to the frontend, you can run the tests for frontend using

.. code-block:: bash

    ./frontend-test.sh

Also, run the **integration tests** for ListenBrainz.

.. code-block:: bash

   ./integration-test.sh

When the tests complete, you will see if your changes are valid or not. These tests
are a helpful way to validate new changes without a lot of work.


Lint your code
--------------

ListenBrainz uses ESLint to lint the frontend codebase, please make sure you lint
all new frontend code using

.. code-block:: bash

    ./lint.sh

This command should list all issues with the code you've modified. Make sure to fix
all errors.

.. note::

    You might need to rebuild the `static_builder` image before running the linter,
    this can be done using,

    .. code-block:: bash

        ./develop build static_builder