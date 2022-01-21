Updating Production Database Schema
===================================

.. warning::

    The production database cluster is serious business 😱. Think twice whenever interacting with it and check with
    others in face of the slightest doubt.

The listenbrainz image on which most of ListenBrainz containers run has the :command:`psql` command installed. You can
`exec` into a container and use the :command:`psql` to connect to the relevant database and execute scripts. The
connection parameters to connect to the databases are in :file:`/code/listenbrainz/listenbrainz/config.py`.

Whenever modifying the database, run the sql commands inside a transaction if possible. Once you have started the
transaction, execute the commands you want to. Do not commit the transaction yet. Double check the state of the database
to ensure the changes are in line with what you expect. If so commit the transaction otherwise rollback and contact
other maintainers.
