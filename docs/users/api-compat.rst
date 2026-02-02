=======================================
Last.FM Compatible API for ListenBrainz
=======================================

There are two versions of the Last.FM API used by clients to submit data to Last.FM.

#. `The latest Last.FM API <https://www.last.fm/api>`_

#. `The AudioScrobbler API v1.2 <http://www.audioscrobbler.net/development/protocol/>`_

ListenBrainz can understand requests sent to both these APIs and use their data to import listens submitted by clients like VLC and Spotify. Existing Last.FM clients can be pointed to the `ListenBrainz proxy URL <http://proxy.listenbrainz.org>`_ and they should submit listens to ListenBrainz instead of Last.FM.

*Note*: This information is also present on the `ListenBrainz website <https://listenbrainz.org/lastfm-proxy>`_.

AudioScrobbler API v1.2
=======================

Clients supporting the old version of the AudioScrobbler API (such as VLC and Spotify) can be configured to work with ListenBrainz by making the client point to ``http://proxy.listenbrainz.org`` and using your MusicBrainz ID as username and the `LB Authorization Token <https://listenbrainz.org/settings/>`_ as password.

If the software you are using doesn't support changing where the client submits info (like Spotify), you can edit your ``/etc/hosts`` file as follows::

       138.201.169.196    post.audioscrobbler.com
       138.201.169.196    post2.audioscrobbler.com


Last.FM API
===========

*These instructions are for setting up usage of the Last.FM API for Audacious client on Ubuntu. These steps can be modified for other clients as well.*

For development
---------------

#. Install dependencies from `here <http://redmine.audacious-media-player.org/boards/1/topics/788>`_, then clone the repo and install audacious.

#. Before installing audacious-plugins, edit the file `audacious-plugins/src/scrobbler2/scrobbler.h` to update the following setting on line L28. This is required only because the local server does not have https support.::

   `SCROBBLER_URL` to "http://ws.audioscrobbler.com/2.0/".

#. Compile and install the plugins from the instructions given `here <http://redmine.audacious-media-player.org/boards/1/topics/788>`_.

#. Edit the ``/etc/hosts`` file and add the following entry::

     127.0.0.1 ws.audioscrobbler.com

#. Flush dns and restart network manager using::

    $ sudo /etc/init.d/dns-clean start
    $ sudo /etc/init.d/networking restart

#. Register an application on MusicBrainz with the following Callback URL ``http://<HOSTURL>/login/musicbrainz/post`` and update the received MusicBrainz Client ID and Client Secret in config.py of ListenBrainz. ``HOSTURL`` should be as per the settings of the server. Example: ``localhost``

#. In Audacious, go to File > Settings > Plugins > Scrobbler2.0 and enable it. Now open its settings and then authenticate.

#. When you get a URL from your application which look like this ``http://last.fm/api/auth/?api_key=as3..234&..``, replace it with ``http://<HOSTURL>/api/auth/?api_key=as3..234&..``.
    - If you are running a local server, then ``HOSTURL`` should be similar to "localhost:7080".
    - If you are not running the server, then ``HOSTURL`` should be "api.listenbrainz.org".


For users
---------

#. Repeat all the above steps, except for steps 2 and 6.

#. For Step 8, choose the 2nd option for ``HOSTURL``.
