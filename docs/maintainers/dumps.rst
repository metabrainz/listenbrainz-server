Data Dumps
==========

Check FTP Dumps age script
^^^^^^^^^^^^^^^^^^^^^^^^^^
Dumps may fail in production due to many reasons. We have a script to check the latest dump available on the FTP is
younger than a specified timeframe. If the latest dump is older, an email is sent to the maintainers. This email
is usually responsible for bringing dump failures to the notice of maintainers. This script is part of the ListenBrainz
cron jobs and is scheduled to run a few hours after the regular dump times. If dumps are not working but no email was
received by the maintainers, it is possible that the cron jobs are not setup properly.

Twice monthly dumps
^^^^^^^^^^^^^^^^^^^
The twice monthly dumps are created by two independent cron jobs, both publishing into the :file:`fullexport` directory
on the FTP server:

* the **db** dump job creates the public and private postgres and timescale dumps into a
  :file:`listenbrainz-dump-<id>-<timestamp>-db` directory.
* the **full** dump job creates the listens, spark and statistics dumps into a
  :file:`listenbrainz-dump-<id>-<timestamp>-full` directory.

The full dump runs on the 1st and 15th of each month, and the db dump runs on the 2nd and 16th. The jobs run on separate
hosts, so scheduling them on different days prevents them from reading heavily from the databases at the same time.
Both dump types get their own id in the :code:`data_dump` table, so their ids and timestamps do not match each other.

Logs
^^^^
Looking at the logs is a good starting point to debug dump failures. Database, incremental, feedback, and canonical dump
jobs run in the :code:`listenbrainz-cron-prod` container. Full dump jobs run in the
:code:`listenbrainz-full-dumps-cron-prod` container. The output of dump-related jobs is redirected in the crontab files
under :file:`docker/services/cron/`.

For full dumps, inspect :file:`/logs/full_dumps.log` inside the full-dumps cron container:
:code:`docker exec -it listenbrainz-full-dumps-cron-prod bash`. For other dump jobs, open a bash shell in the regular
cron container by running :code:`docker exec -it listenbrainz-cron-prod bash`. The db dump job logs to
:file:`/logs/db_dumps.log` there.

This file is large, so use :command:`tail` instead of :command:`cat` to view the logs. For example:
:code:`tail -n 500 /logs/full_dumps.log` will list the last 500 lines of the full dumps log file.

Full dump retention
^^^^^^^^^^^^^^^^^^^
Full listens dump payloads are removed from local FTP staging after a successful rsync. Small marker directories remain
so that later rsync runs preserve the newest full dumps on the FTP server and remove only versions beyond the retention
limit. :data:`listenbrainz.dumps.cleanup.NUMBER_OF_FULL_DUMPS_TO_KEEP` controls that limit and is currently ``2``.
Retention cleanup runs only after every pending public payload uploads successfully, so failed uploads remain locally
available for retry. Public full dumps left on the legacy backup volume are removed during the next full-dump run.

Db dumps are much smaller, so they are handled like the incremental dumps instead: the public dumps stay in the FTP
staging directory and are also copied to the backup volume, and the private dumps are kept on the private backup volume
and are never uploaded to FTP. :data:`listenbrainz.dumps.cleanup.NUMBER_OF_DB_DUMPS_TO_KEEP` controls how many of them
are retained in each of those locations. Because both dump types share the :file:`fullexport` directory, the db dump
rsync protects the retained full dump payloads on the FTP server from deletion.

From the log file, you should probably be able to see whether the error occurred in python part of the code or bash
script. If you see a python stack trace, it is likely that sentry recorded the error too. The `sentry view <https://sentry.metabrainz.org/organizations/metabrainz/issues/?project=15>`_
sometimes offers more details so searching sentry for this error can be helpful.

Manually triggering dumps
^^^^^^^^^^^^^^^^^^^^^^^^^
.. program:: ./develop.sh manage dump create_full

If you want to re-run a dump after it fails, or manually trigger a dump then you can run the dump script manually. A few
things need to be kept in mind while doing this, the :ref:`developers/commands:create_full` and
:ref:`developers/commands:create_db_dump` commands invoked to do the dumps accept a :option:`--dump-id` parameter to number
the dump. If no id is specified, the script will look in the database for the last id, add 1 to it and use it for the dump.
A supplied dump id must belong to an existing dump of the same type: a db dump cannot be re-run with the id of a full
dump, or vice versa.

.. code:: sql

  select * from data_dump order by created desc;

If a dump failed too early in the script, it won't have an id in the database. Otherwise, it will have created one
before failing. To be sure, check the :code:`data_dump` table in the database. If the id exists and the dump had failed
, it makes sense to reuse that dump id when generating the dump again manually.

Also the bash script to create dumps performs setup, cleanup and syncing to FTP tasks so do not invoke the python
command directly. The bash script forwards arguments to the python command so you can pass any arguments that the python
command accepts to it as well. Run full dump commands from :code:`listenbrainz-full-dumps-cron-prod`; run other dump
commands from :code:`listenbrainz-cron-prod`. See the current version of the script in the repository for more details.
Here is an example of how you can manually specify the id of the dump (copied the cronjob command at the time of writing
and added the argument before redirecting):

.. code:: bash

    flock -x -n /var/lock/lb-incremental-dumps.lock /code/listenbrainz/admin/create-dumps.sh incremental --dump-id 700 >> /logs/incremental_dumps.log 2>&1

.. note::

    Full dumps take over 12 hours to complete. If you run the command directly and close the terminal before full dumps
    completion, the dumps will get interrupted and fail. So either run the command inside a :command:`tmux` session
    or use a combination of :command:`nohup` and :command:`&` with the dump command.
