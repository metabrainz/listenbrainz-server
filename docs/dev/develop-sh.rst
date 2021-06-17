Using develop.sh
----------------

We provide a utility to wrap docker-compose and some common development processes.

To open a psql session to the listenbrainz database, run:

.. code-block:: bash

    ./develop.sh psql

To open a psql session to the timescale database containing user listens, run:

.. code-block:: bash

    ./develop.sh timescale

To open a bash shell in the webserver container, run:

.. code-block:: bash

    ./develop.sh bash

To open flask shell in the webserver container using ipython with the listenbrainz app loaded, run:

.. code-block:: bash

    ./develop.sh shell

To open a redis shell:

.. code-block:: bash

    ./develop.sh redis

``develop.sh`` provides a direct interface to invoke manage.py inside a docker container.
manage.py is a click script containing a number of listenbrainz management commands.
To invoke manage.py, run:

.. code-block:: bash

    ./develop.sh manage <command>

To get a list of manage.py commands, run:

.. code-block:: bash

    ./develop.sh manage --help

To pass any other command to docker-compose, run:

.. code-block:: bash

    ./develop.sh <command>

To get a list of valid docker-compose commands, see the output of ``docker-compose help``:

.. code-block:: bash

    ./develop.sh help
