Production Deployment
=====================

.. note::

    This documentation is for ListenBrainz maintainers for when they deploy the website

Listenstore maintenance
^^^^^^^^^^^^^^^^^^^^^^^

Set the Consul key ``listenstore_up`` to the JSON boolean ``false`` to disable
webserver access to the listenstore during maintenance. This key supplies the
``LISTENSTORE_UP`` application setting; for local development, set
``LISTENSTORE_UP = False`` in ``listenbrainz/config.py`` instead.

When disabled, startup skips creating the listenstore instance. Endpoints protected
by ``api_listenstore_needed`` return HTTP 503, and pages protected by ``web_listenstore_needed``
redirect to the listens-offline page.

To restore listenstore access, set ``listenstore_up`` to the JSON boolean
``true`` (or ``LISTENSTORE_UP = True`` locally), regenerate the configuration,
and restart the webserver processes again.

Cron
^^^^

You can cleanly shut down cron from ``docker-server-configs`` by running

.. code-block:: bash

    ./scripts/terminate_lb_cron.sh

If no cron jobs are running, this will stop and delete the cron container. If a job is running
it will notify you and not stop the container.
