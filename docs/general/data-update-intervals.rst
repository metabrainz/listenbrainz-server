ListenBrainz Data Update Intervals
==================================

Expected schedule:

=============================================== =========================================
System                                          Update schedule
=============================================== =========================================
Receiving listens, updating listen counts		Immediate
Deleting listens					            Removed at the top of the next hour (UTC)
Updating statistics for new listens			    Daily
Removing deleted listens from stats			    On the 2nd and 16th of each month
Full dumps						                1st and 15th of each month
Incremental dumps					            Daily
=============================================== =========================================

Situations will occasionally arise where these take longer. If you have been a very patient user, and
something still hasn't updated, check our `forum https://community.metabrainz.org/`_ for news or discussion.
If you suspect something has gone very wrong you can also search for tickets, and lodge new tickets, in our
`ticket tracker https://community.metabrainz.org/`_.

This complicated schedule is caused by ListenBrainz having a lot of interconnected parts that work at
different scales. For more details, read on!


Listens and Listen Counts
^^^^^^^^^^^^^^^^^^^^^^^^^

Listen submitted via the ListenBrainz API should appear in your Dashboard immediately. The Spotify API does
not immediately report completed listens; it may take several minutes for these to be reported to ListenBrainz.

Listen Count should always be up to date for listens that we have received. The only time we deviate
from this is when listens are to be deleted. Deleting a listen is (surprisingly) a fairly expensive operation
and we have the resources for keeping listen counts updated, but not to keep listen counts fully up to date
when listens are being deleted. Any listens marked for deletion will be deleted at the top of the next hour.
Once this happens, your listen counts will be consistent again.

We’ve spent months working on making this system work well and be scalable. This system is surprisingly
complex and it took us several approaches to get to where we are now. It isn’t ideal but, given our limited
resources, we opted for what we call an “eventually consistent” system that focuses on being consistent
(accurate) for most of our users most of the time.


User Statistics
^^^^^^^^^^^^^^^

Calculating user statistics is an entirely different and challenging task! For this we utilize the Spark
database system (more on this below), which requires us to dump, copy and import many gigabytes of data
from our Postgres database into Spark.

Currently, we use our data dumps for this purpose – we dump the full data twice a month on the 1st and
15th of the month and dump incremental dumps on a daily basis. The daily dumps update the listen data in
our Spark system with new listens, but they do not remove any listens from Spark that may have been deleted
from the main database since the last incremental dump. Deleted listens are removed from Spark only when we
import a new full data dump on the 2nd and 16th day of the month.

For example: If you delete a listen on the 5th day of the month, you can expect that the statistics generated
on the 17th will reflect the current stats of your listens as of the end of the 14th day of the month.

We recognize that this is less than ideal – we’re considering how to improve this and to make the ingestion
of listens and the deletion of listens both happen in real time.

MusicBrainz Metadata Cache
^^^^^^^^^^^^^^^^^^^^^^^^^^

Our MBID Mapping system maps incoming listens to the correct MusicBrainz metadata. It may take up to 4 hours
for data entered into MusicBrainz to become available in the mapping system or for manual mapping (manually
linking listens to MusicBrainz entities).

ListenBrainz data infrastructure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ListenBrainz project makes use of three major types of databases: Postgres/Timescale, Spark and CouchDB.
Postgres is our primary workhorse that serves user data (accounts, followers, likes/hates, etc). Timescale
(an extended version of Postgres) is used to store Listens and Playlists. Postgres and Timescale are fantastic
tools for providing a specific piece of information quickly (e.g which users does this a user follow).
However Postgres/Timescale are not great for inserting large amounts of data into the database each day – it
slows everything down for everyone. So we store the computed user listening statistics in CouchDB, which is
suitable for ingesting large volumes of data and serving it for a day, before it is replaced with the next
iteration of the data.

Finally, we have Spark, which is a batch processing system. Spark is designed to work with large datasets in a
batch fashion, where the data for *all* users might be processed in one batch task. Spark works with huge amounts
of data in one go, which is very distinct from our use of Postgres/Timescale and CouchDB.

All of the tools we use are excellent open source tools. Each does a fantastic job, at the tasks they were
designed for. There is no one open source solution for all of our needs, so we shuffle data from one system to
another as we need it. This, however, brings latency and delays in keeping all of our data up to date.

Take a look at the general overview of how data flows between each of these systems:

.. image:: ../images/dataflows-graph.png
  :alt: ListenBrainz Data Flow Graph

In the future we hope to serve content (stats) directly from our Spark installation (with the help of 
existing tools) as indicated by the dotted arrow between Spark and the API/web pages box. This will further
reduce the latency of some of our services.
