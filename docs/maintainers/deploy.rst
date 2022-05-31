Production Deployment
=====================

.. note::

    This documentation is for ListenBrainz maintainers for when they deploy the website

Cron
^^^^

You can cleanly shut down cron from ``docker-server-configs`` by running

.. code-block:: bash

    ./scripts/terminate_lb_cron.sh

If no cron jobs are running, this will stop and delete the cron container. If a job is running
it will notify you and not stop the container.
