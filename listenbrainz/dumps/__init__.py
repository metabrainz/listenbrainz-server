""" This module contains data dump creation and import functions.

Read more about the data dumps in our documentation here:
https://listenbrainz.readthedocs.io/en/latest/users/listenbrainz-dumps.html
"""

DUMP_DEFAULT_THREAD_COUNT = 4

# The schema version of the core database. This includes data in the "user" database
# (tables created from ./admin/sql/create-tables.sql) and includes user data,
# statistics, feedback, and results of user interaction on the site.
# This value must be incremented after schema changes on tables that are included in the
# public dump
SCHEMA_VERSION_CORE = 8
