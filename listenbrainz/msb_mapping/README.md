Introduction
============

This sub-project calculates the Messybrainz <=> MusicBrainz mapping. To run it, you'll need a copy of the
musicbrainz database and a copy of the messybrainz database. To create the mapping requires rather a lot of 
RAM. When this software was developed a 64GB server was used.

The current setup of this code is geared to run on the MetaBrainz infrastructure on the williams server.
The messybrainz-mapper container is a cron job container that does nothing but run the mapping scripts
periodically. See docker/crontab for the current schedule.

To run a mapping do:

```docker exec -it messybrainz-mapper python manage.py create-all```

To test the mapping when it is generated, run:

```docker exec -it messybrainz-mapper python manage.py test-mapping```

To inspect the cron log of the container do:

```docker exec -it messybrainz-mapper python manage.py cron-log```


Future improvements
-------------------

Very soon, (in the next few weeks at the latest) this code needs a few more improvements:

1. Add sentry support to give feedback about the status of cron jobs and if something has failed.
2. Add a develop.sh file and documentation on how to use it for local development.
3. Add support for taking generated dump files and moving them to the FTP server
