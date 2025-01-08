RabbitMQ
========

Maintenance
~~~~~~~~~~~

Tolerance to connectivity issues
++++++++++++++++++++++++++++++++

RabbitMQ is a mandatory service required by consul-template config used in common by almost all ListenBrainz containers.
Therefore, ListenBrainz will refuse to come up if no RabbitMQ instance is running. If an instance is available but
there are connectivity issues, various ListenBrainz services will remain up but throw errors while trying to perform
some functions.

The most important part that relies on RabbitMQ is the listens submission API. If RabbitMQ is unreachable, users will
be unable to submit listens to ListenBrainz.

Maintenance mode
++++++++++++++++

It doesn’t exist. To perform maintenance operations, ListenBrainz requires switching to another instance
of RabbitMQ to prevent any data loss, even for a short period of time.

Data importance
+++++++++++++++

ListenBrainz uses RabbitMQ in various places, for a brief overview :ref:`see listen flow <listen-flow>`. The most
important is listens submission. Listens are published to the `incoming` exchange and expected to be persisted durably
until the timescale writer has acknowledged writing those to the database. This data is of utmost importance.

Other uses of RabbitMQ in ListenBrainz include delivering now playing listens to websockets, unique listens to the mbid
mapping writer, results from spark cluster to the database etc. In these cases, the data can be regenerated. Data loss
in these cases is tolerable as long as it is known that some messages were lost.

Data persistence
++++++++++++++++

Messages are expected to be processed within seconds (or minutes during activity peaks), but because of the importance
of the listen data a persistent volume is needed. Listen data messages are critical and should be backed up, other
messages can be regenerated and can be ignored in case of a disaster.

Procedures
++++++++++

* Start service: LB containers automatically connect to RabbitMQ on startup.
* Reload service configuration: Update the RabbitMQ service details in consul configuration for LB and deploy a new image.
* Restart service: Restart LB docker containers and each container will disconnect and reconnect to RabbitMQ.
* Move service:

   * Create vhost, user, permissions, queues in the new instance
   * Stop LB producers (except the web and api containers)
   * Use shovels to transfer existing messages from old RabbitMQ instance to new one
   * Build an image using the a new consul config pointing to new RabbitMQ instance
   * Deploy all consumers using the new image
   * Deploy all producers using the new image
   * Stop shovels

  There will be no data loss but a short downtime while the containers restart.
* Remove service: LB cannot function without RabbitMQ. So the only way is to stop LB containers, and LB will become unavailable.

Implementation details
~~~~~~~~~~~~~~~~~~~~~~

* Connectivity issues are reported through both Docker logs and Sentry.
* ListenBrainz has multiple producers and consumers.
* message protocol version: AMQP 0.9.1.
* heartbeat timeout: client sets to 0, rabbitmq will use the server specified value.
* ack mode:

   * producers do not use any ack mode.
   * auto ack: `spark-request-consumer-michael`
   * manual ack: all other consumers

* Each connection identifies itself with RabbitMQ server by using the name of the docker container in which the service is running.
