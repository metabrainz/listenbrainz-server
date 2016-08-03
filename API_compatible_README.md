# API Compatible

*Instructions are for setting up API for Audacious client on Ubuntu. The steps can be modified for other clients as well.*

### For development
1. Install dependencies from [here](http://redmine.audacious-media-player.org/boards/1/topics/788) then clone the repo and install audacious.
2. Before installing audacious-plugins, edit the file `audacious-plugins/src/scrobbler2/scrobbler.h` to update the following setting on line L28. This is required only because the local server does not have https support.  
  - `SCROBBLER_URL` to "http://ws.audioscrobbler.com/2.0/".  
3. Compile and install the plugins from the instructions given in [here](http://redmine.audacious-media-player.org/boards/1/topics/788).  
4. Edit the `/etc/hosts` file and add the following entry.  

  > 127.0.0.1 ws.audioscrobbler.com  

 Flush dns and restart network manager using:  
 `sudo /etc/init.d/dns-clean start`  
 `sudo /etc/init.d/networking restart`  
5. Register an application on musicbrainz with the following callback URL "http://\<HOSTURL\>/login/musicbrainz/post" and update the received client-id and client-secret in config.py of listenbrainz. HOSTURL should be as per the settings of the server. Ex, "localhost:8080"  
6. In audacious, goto, File > Settings > Plugins > Scrobbler2.0 and enable it. Now Open its settings and then authenticate.  
7. When you get a URL from your application which look like this "http://last.fm/api/auth/?api_key=as3..234&..", replace it with "http://\<HOSTURL\>/api/auth/?api_key=as3..234&..".
  - If you are running a local server, then HOSTURL should be similar to "localhost:8080".  
  - If you are not running the server, then HOSTURL should be "listenbrainz.org".  
8. Once done, Enjoy!


### For users
- Repeat all the above steps, except for steps `Step2` and `Step5`
- For `Step7` choose the 2nd option.
