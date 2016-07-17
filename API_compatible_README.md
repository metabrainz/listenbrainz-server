# API Compatible

*Instructions are for setting up API for Audacious client on Ubuntu. The steps can be modified for other clients as well.*

**SOURCE_1**: http://redmine.audacious-media-player.org/boards/1/topics/788

1. Install dependencies from **SOURCE_1** then clone the repo and install audacious.
2. Before installing audacious-plugins, edit the file `audacious-plugins/src/scrobbler2/scrobbler.h` to update the following settings on lines L26-L28.  
  - `SCROBBLER_API_KEY` to the key given on "listenbrainz.org/user/import" page.
  - `SCROBBLER_URL` to "http://last.fm/2.0/".  
  Now compile and install the plugins from the instructions given in **SOURCE_1**.
3. Register an application on musicbrainz with the following callback URL "http://www.last.fm/login/musicbrainz/post"
4. Update the received client-id and client-secret in config.py of listenbrainz.
5. Edit the `/etc/hosts` file and add the following entries.

  > 127.0.0.1 http://www.last.fm  
  > 127.0.0.1 www.last.fm  
  > 127.0.0.1 last.fm  

  Flush dns and restart network manager using:  
  `sudo /etc/init.d/dns-clean start`  
  `sudo /etc/init.d/networking restart`  
6. In audacious, goto, File > Settings > Plugins > Scrobbler2.0 and enable it. Now Open its settings and then authenticate.  
7. Once done, Enjoy!
