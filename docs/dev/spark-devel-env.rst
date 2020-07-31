Set up ListenBrainz Spark development environment
=================================================

There are two distinct part of the ListenBrainz development environment:

1. listenbrainz -- the actual webserver components of ListenBrainz
2. listenbrainz_spark -- the spark environment used for features that involve data processing (stats, recommendations etc.)

If you're just working on adding a feature to the ListenBrainz webserver, you **do not** need
to set up the Spark development environment. However, if you're looking to add
a new stat or improve our fledgling recommender system, you'll need both the webserver
and the spark development environment.

This guide should explain how to develop and test new features for ListenBrainz that use Spark.

Set up the webserver
--------------------
The spark environment is dependent on the webserver. Follow the steps in the :doc:`guide to set up the webserver environment <devel-env>`.

Create listenbrainz_spark/config.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The spark environment needs a config.py in the listenbrainz_spark/ dir. Create it by copying from the sample config file.

.. code-block:: bash

    cp listenbrainz_spark/config.py.sample listenbrainz_spark/config.py


Initialize ListenBrainz Spark containers
----------------------------------------

Run the following command to build the spark containers.

.. code-block:: bash

    ./develop.sh spark build

The first time you build the containers, you also need to format the ``namenode``
container.

.. code-block:: bash

    ./develop.sh spark format

.. info::

    You can run ``./develop.sh spark format`` any time that you want to delete all of the
    data that is loaded in spark. This will shut down the spark docker cluster, remove
    the docker volumes used to store the data, and recreate the HDFS filesystem.


Your development environment is now ready. Now, let's actually see ListenBrainz Spark
in action!


Bring containers up
--------------------

Start the ListenBrainz Spark containers by executing ``develop.sh spark up``.

.. code-block:: bash

    ./develop.sh spark up

Import data into the spark environment
--------------------------------------

We provide small data dumps that are helpful for working with real ListenBrainz data.
Download and import a data dump into your spark environment using the following
commands.

.. code-block:: bash

    ./develop.sh spark run request_consumer python spark_manage.py upload_listens -i


Now, you are all set to begin making changes and seeing them in real-time inside
of your development environment!

Once you are done with your work, shut down the containers using the following command.

.. code-block:: bash

    ./develop.sh spark down

.. note::

    You'll need to run ``./develop.sh spark down`` every time you restart your environment, otherwise hadoop errors out.

Working with request_consumer
-----------------------------

The ListenBrainz webserver and spark cluster interact with each other via the request consumer. For a more detailed
guide on working with the request consumer, read this :doc:`document <spark-architecture>`.

Test your changes with unit tests
---------------------------------

Unit tests are an important part of ListenBrainz Spark. It helps make it easier for
developers to test changes and help prevent easily avoidable mistakes later on.
Before committing new code or making a pull request, run the unit tests on your
code.

.. code-block:: bash

   ./test.sh spark

This builds and runs the containers needed for the tests. This script configures
test-specific data volumes so that test data is isolated from your development
data.

When the tests complete, you will see if your changes are valid or not. These tests
are a helpful way to validate new changes without a lot of work.

Refer the :doc:`FAQs <faqs>` to resolve the common errors that may arise when setting up
the development environment.
