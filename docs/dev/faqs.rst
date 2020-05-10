FAQs
====

**What to do if getting an error while running ``./develop.sh build`` command, 'ERROR: Couldn't connect to Docker daemon at http+docker://localhost - is it running?'?**

- You need to add the user to the docker group by entering the following command in the terminal:

  .. code-block:: bash

    sudo usermod -aG docker $USER

- After this command, restart the computer and then again run ``./develop.sh build.``
|

**How to resolve 'datanode is running as process 1. Stop it first' or 'namenode is running as process 1. Stop it first'?**

- You need to shut down the previous containers before bringing them up again. Run the following command to shut down the containers:

  .. code-block:: bash

    ./develop.sh spark down

- When the containers shut down, run ``./develop.sh spark up`` again.
|

**How to resolve 'sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) FATAL: role "listenbrainz" does not exist' on running './test.sh'?**

- You need to shut down the previous test containers before bringing them up again. Run the following command to shut down the test containers:

  .. code-block:: bash

    ./test.sh -d

- When the containers shut down, run ``./test.sh`` to run the tests again.
