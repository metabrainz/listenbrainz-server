Data Dumps
==========

Check FTP Dumps age script
^^^^^^^^^^^^^^^^^^^^^^^^^^
Dumps may fail in production due to many reasons. We have a script to check the latest dump available on the FTP is
younger than a specified timeframe. If the latest dump is older, an email is sent to the maintainers. This email
is usually responsible for bringing dump failures to the notice of maintainers. This script is part of the ListenBrainz
cron jobs and is scheduled to run a few hours after the regular dump times. If dumps are not working but no email was
received by the maintainers, it is possible that the cron jobs are not setup properly.

Logs
^^^^
Looking at the logs is a good starting point to debug dump failures, the log file is located at :file:`/logs/dumps.log`
inside the listenbrainz-cron-prod container. The output of dump-related jobs is `redirected in the crontab <https://github.com/metabrainz/listenbrainz-server/blob/1f2e2634126a32a75bdb717b741d55099f4dd411/docker/services/cron/crontab#L8-L19>`_
. Open a bash shell in the cron container by running :code:`docker exec -it listenbrainz-cron-prod bash`.

This file is large, so use :command:`tail` instead of :command:`cat` to view the logs. For example:
:code:`tail -n 500 /logs/dumps.log` will list the last 500 lines of the log file.

From the log file, you should probably be able to see whether the error occurred in python part of the code or bash
script. If you see a python stack trace, it is likely that sentry recorded the error too. The `sentry view <https://sentry.metabrainz.org/organizations/metabrainz/issues/?project=15>`_
sometimes offers more details so searching sentry for this error can be helpful.

Manually triggering dumps
^^^^^^^^^^^^^^^^^^^^^^^^^
.. program:: ./develop.sh manage dump create_full

If you want to re-run a dump after it fails, or manually trigger a dump then you can run the dump script manually. A few
things need to be kept in mind while doing this, the :ref:`developers/commands:create_full` invoked to do the dump
accepts a :option:`--dump-id` parameter to number the dump. If no id specified, the script will look in the database for
the last id, add 1 to it and use it for the dump.

.. code:: sql

  select * from data_dump order by created desc;

If a dump failed too early in the script, it won't have an id in the database. Otherwise, it will have created one
before failing. To be sure, check the :code:`data_dump` table in the database. If the id exists and the dump had failed
, it makes sense to reuse that dump id when generating the dump again manually.

Also the bash script to create dumps performs setup, cleanup and syncing to FTP tasks so do not invoke the python
command directly. The bash script forwards arguments to the python command so you can pass any arguments that the python
command accepts to it as well. See the current version of the script in the repository for more details. Here is an
example of how you can manually specify the id of the dump (copied the cronjob command at the time of writing and
added the argument before redirecting):

.. code:: bash

    flock -x -n /var/lock/lb-dumps.lock /code/listenbrainz/admin/create-dumps.sh incremental --dump-id 700 >> /logs/dumps.log 2>&1

.. note::

    Full dumps take over 12 hours to complete. If you run the command directly and close the terminal before full dumps
    completion, the dumps will get interrupted and fail. So either run the command inside a :command:`tmux` session
    or use a combination of :command:`nohup` and :command:`&` with the dump command.
