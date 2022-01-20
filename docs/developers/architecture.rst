=========================
ListenBrainz Architecture
=========================

Production Services
================================

Services exclusive to ListenBrainz
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1) listenbrainz-cron-prod: runs cron jobs used to execute periodic tasks like creating dumps, invoking spark jobs to
   import dump, requesting statistics and so on.

2) listenbrainz-web-prod: runs a uwsgi server which serves ListenBrainz flask app for the website and APIs
   (except compat APIs).

3) listenbrainz-api-compat-prod: runs a uwsgi server which serves a flask app for only Last.fm compatible APIs.

4) listenbrainz-api-compat-nginx-prod: ???

5) listenbrainz-timescale-writer-prod: runs timescale writer which consumes listens from incoming rabbitmq queue,
   performs a messybrainz lookup and inserts listens in the database.

6) listenbrainz-websockets-prod: runs websockets server to handle realtime listen and playlist updates.

7) listenbrainz-labs-api-prod: runs a uwsgi server which serves a flask app for experimental ListenBrainz APIs.

8) listenbrainz-spotify-reader-prod: runs a service for importing listens from spotify API and submitting to rabbitmq.

9) listenbrainz-spark-reader-prod: processes incoming results from spark cluster like inserting statistics in database etc.

10) listenbrainz-redis: redis instance used for caching all stuff LB.

11) exim-relay-listenbrainz.org: smtp relay used by LB to send emails.

12) listenbrainz-timescale: timescale instance for LB to store listens and playlists.

13) listenbrainz-typesense, listenbrainz-mbid-mapping, listenbrainz-mbid-mapping-writer-prod: ???

14) listenbrainz spark cluster: spark cluster to generate statistics and recommendations for LB.

Services not exclusive to ListenBrainz
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

15) postgres-floyd: primary database instance shared by multiple MetaBrainz projects. The main ListenBrainz DB resides here as well as the MessyBrainz DB.

16) rabbitmq-clash: rabbitmq instance shared by MetaBrainz services. listenbrainz queues are under /listenbrainz vhost.

Listen Flow
===========

.. image:: ../images/listen-flow.svg
   :alt: How listens flow in ListenBrainz

Listens can be submitted to ListenBrainz using native ListenBrainz API, Last.fm compatible API (API compat) and
AudioScrobbler 1.2 compatible API (API compat deprecated). Each api endpoint validates the listens submitted through it
and sends the listens to a RabbitMQ queue based on listen type. Playing Now listens have a different queue from
"Permanent" listens (Incoming queue).

Playing now listens are ephemeral and not stored in the database but in Redis cache with an appropriate expiry time. The
Playing now queue is consumed by Websockets service. The frontend connects with the Websockets service to display
listens on the website without manually reloading the page.

On the other hand, "Permanent" Listens need to be persisted in the database. Timescale Writer service consumes from the
Incoming queue. It begins with querying the MessyBrainz database for MessyBrainz IDs. MessyBrainz tries to
find an existing match for the hash of the listen in the database. If one exists, it is returned otherwise it inserts
the hash and data into the database and returns a new MessyBrainz ID.

Once the writer receives MSIDs from MessyBrainz, it combines those with the listens and inserts the listens in the
listen table. The insert deduplicate listens based on a (user, timestamp, track) triplet i.e. at a given timestamp,
a user can have a track entry only once. As you can see, listens of different tracks at the same timestamp are allowed
for a user. The database returns the "unique" listens to the writer which publishes those to Unique queue.

Websockets consume from the unique queue for the same purpose as with now playing listens. The MBID mapper also consumes
from the unique queue and builds a MSID->MBID mapping using these listens.

Frontend Rendering
==================

ListenBrainz frontend pages are a blend of Jinja2 templates (Python) and React components (Javascript). The Jinja2 templates used are bare bones
, they include a placeholder div called `react-container` into which the react components are rendered. To render the
components, some data like current user info, api url etc are needed. These are injected as json into two script tags in the HTML page, to be consumed by the React application:
page-react-props and global-react-props.

Most ListenBrainz pages will have a Jinja2 template and at least 1 React component file. The components are written in Typescript, and we use Webpack to transpile them to javascript, to compile CSS from LESS and to minify and bundle everything. This is all done in a separate Docker container which watches for changes in front-end files and recompiles automatically. Using script tags, we manually specify the
appropriate compiled javascript file to include on a given page in its Jinja2 template.
