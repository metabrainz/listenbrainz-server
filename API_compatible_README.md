# API Compatible

*Instructions are for setting up API for Audacious client on Ubuntu. The steps can be modified for other clients as well.*

**SOURCE_1**: http://redmine.audacious-media-player.org/boards/1/topics/788

### For development
1. Install dependencies from **SOURCE_1** then clone the repo and install audacious.
2. Before installing audacious-plugins, edit the file `audacious-plugins/src/scrobbler2/scrobbler.h` to update the following setting on line L28. This is required only because the local server does not have https support.  
  - `SCROBBLER_URL` to "http://ws.audioscrobbler.com/2.0/".  
3. Compile and install the plugins from the instructions given in **SOURCE_1**.  
4. Edit the `/etc/hosts` file and add the following entry.  

  > 127.0.0.1 ws.audioscrobbler.com  

 Flush dns and restart network manager using:  
 `sudo /etc/init.d/dns-clean start`  
 `sudo /etc/init.d/networking restart`  
5. Register an application on musicbrainz with the following callback URL "http://\<hostname\>:\<port\>/login/musicbrainz/post" and update the received client-id and client-secret in config.py of listenbrainz. hostname and port number are as per the server.  
6. In audacious, goto, File > Settings > Plugins > Scrobbler2.0 and enable it. Now Open its settings and then authenticate.  
7. When you get a URL from your application which starts http://last.fm/api/auth, replace it with http://\<hostname\>:\<port\>/.../../...". Hostname is listenbrainz.org if you are not running a local server.  
8. Once done, Enjoy!


### For users
- Repeat all the above steps, except for steps `Step2` and `Step5`
