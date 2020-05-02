Using develop.sh
================

We provide a utility to wrap docker-compose and some common development processes.

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
