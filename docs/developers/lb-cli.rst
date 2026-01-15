ListenBrainz CLI Tool
=====================

The ``lb.py`` CLI tool provides a unified, cross-platform interface for common
development tasks. It wraps docker-compose and management commands in an
easy-to-use command-line interface.

Quick Start
-----------

Initialize your development environment:

.. code-block:: bash

    python lb.py init

Start the development server:

.. code-block:: bash

    python lb.py start

Visit ``http://localhost:8100`` in your browser.

Available Commands
------------------

Core Commands
^^^^^^^^^^^^^

**init** - Initialize development environment

.. code-block:: bash

    python lb.py init           # Full initialization
    python lb.py init --skip-db # Skip database setup

Builds Docker containers and initializes PostgreSQL and TimescaleDB databases.

**start** - Start development environment

.. code-block:: bash

    python lb.py start      # Foreground mode (Ctrl+C to stop)
    python lb.py start -d   # Detached/background mode

**stop** - Stop all containers

.. code-block:: bash

    python lb.py stop

**restart** - Restart containers

.. code-block:: bash

    python lb.py restart        # Restart all services
    python lb.py restart -s web # Restart specific service

**status** - Show container status

.. code-block:: bash

    python lb.py status

Testing Commands
^^^^^^^^^^^^^^^^

**test** - Run tests

.. code-block:: bash

    python lb.py test                              # Run all unit tests
    python lb.py test --build                      # Rebuild before testing
    python lb.py test --type frontend              # Run frontend tests
    python lb.py test --type spark                 # Run Spark tests
    python lb.py test listenbrainz/tests/test.py  # Run specific test file

Database Commands
^^^^^^^^^^^^^^^^^

**db psql** - Open PostgreSQL shell

.. code-block:: bash

    python lb.py db psql

Connects to the main PostgreSQL database for user data, playlists, and metadata.

**db timescale** - Open TimescaleDB shell

.. code-block:: bash

    python lb.py db timescale

Connects to the TimescaleDB database containing time-series listen data.

Utility Commands
^^^^^^^^^^^^^^^^

**logs** - View container logs

.. code-block:: bash

    python lb.py logs              # Show logs from all services
    python lb.py logs web          # Show logs from web service
    python lb.py logs -f           # Follow logs (like tail -f)
    python lb.py logs web -n 50    # Show last 50 lines

**bash** - Open bash shell in web container

.. code-block:: bash

    python lb.py bash

**shell** - Open Flask shell

.. code-block:: bash

    python lb.py shell

Opens an interactive Python shell with the Flask application context loaded.

**manage** - Run management commands

.. code-block:: bash

    python lb.py manage --help                 # Show all management commands
    python lb.py manage init_db --create-db    # Initialize database
    python lb.py manage dump create_full       # Create database dump

**clean** - Clean up containers and volumes

.. code-block:: bash

    python lb.py clean          # Remove containers
    python lb.py clean -v       # Remove containers AND volumes (WARNING: data loss!)

Comparison with develop.sh and test.sh
---------------------------------------

The ``lb.py`` CLI tool is designed to complement and simplify the existing
``develop.sh`` and ``test.sh`` scripts:

+----------------------------+----------------------------------+----------------------+
| Task                       | Traditional                      | lb.py CLI            |
+============================+==================================+======================+
| Initialize database        | ./develop.sh manage init_db      | python lb.py init    |
+----------------------------+----------------------------------+----------------------+
| Start server               | ./develop.sh up                  | python lb.py start   |
+----------------------------+----------------------------------+----------------------+
| Run tests                  | ./test.sh                        | python lb.py test    |
+----------------------------+----------------------------------+----------------------+
| PostgreSQL shell           | ./develop.sh psql                | python lb.py db psql |
+----------------------------+----------------------------------+----------------------+
| View logs                  | docker-compose logs              | python lb.py logs    |
+----------------------------+----------------------------------+----------------------+
| Run manage.py              | ./develop.sh manage <cmd>        | python lb.py manage  |
+----------------------------+----------------------------------+----------------------+

Benefits
--------

* **Cross-platform**: Works on Windows, macOS, and Linux
* **Consistent interface**: Unified command structure across all operations
* **Better UX**: Colored output, helpful messages, and clear error handling
* **Discoverable**: Built-in help system (``python lb.py --help``)
* **Beginner-friendly**: Simpler commands reduce learning curve for new contributors
* **Type-safe**: Python Click provides command validation and argument parsing

Platform-Specific Notes
-----------------------

Windows
^^^^^^^

On Windows, ensure you have Python 3.6+ installed and Docker Desktop running:

.. code-block:: powershell

    python lb.py init
    python lb.py start

The CLI automatically handles Windows-specific path and command differences.

Linux / macOS
^^^^^^^^^^^^^

On Unix-like systems, you can optionally make ``lb.py`` directly executable:

.. code-block:: bash

    chmod +x lb.py
    ./lb.py init
    ./lb.py start

Or continue using ``python lb.py`` for consistency across platforms.

Getting Help
------------

View available commands:

.. code-block:: bash

    python lb.py --help

Get help for specific command:

.. code-block:: bash

    python lb.py init --help
    python lb.py test --help

For more detailed development documentation, see :doc:`devel-env`.
