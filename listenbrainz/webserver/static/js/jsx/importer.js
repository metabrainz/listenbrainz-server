import APIService from './api-service'

class Scrobble {
  constructor(rootScrobbleElement) {
    this.rootScrobbleElement = rootScrobbleElement;
  }
  
  lastfmID() {
    // Returns url of type "http://www.last.fm/music/Mot%C3%B6rhead"
    if ('url' in this.rootScrobbleElement && this.rootScrobbleElement['url'] !== "" ) {
      let url = this.rootScrobbleElement['url'];
      url = url.split("/");
      return url.slice(0, parts.length-2).join("/");
    } else {
      return "";
    }
  }
  
  artistName() {
    if ('artist' in this.rootScrobbleElement && '#text' in this.rootScrobbleElement['artist']) {
      return this.rootScrobbleElement['artist']['#text'];
    } else {
      return "";
    }
  }
  
  trackName() {
    if ('name' in this.rootScrobbleElement) {
      return this.rootScrobbleElement['name'];
    } else {
      return "";
    }
  }
  
  releaseName() {
    if ('album' in this.rootScrobbleElement && '#text' in this.rootScrobbleElement['album']) {
      return this.rootScrobbleElement['album']['#text'];
    } else {
      return "";
    }
  };
  
  scrobbledAt() {
    if ('date' in this.rootScrobbleElement && 'uts' in this.rootScrobbleElement['date']) {
      return this.rootScrobbleElement['date']['uts'];
    } else {
      /*
      The audioscrobbler API's output differs when the user is playing song.
      In case, when the user is playing song, the API returns 1st listen with
      attribute as {"@attr": {"now_playing":"true"}} while other listens with
      attribute as {"date": {"utc":"12345756", "#text":"21 Jul 2016, 10:22"}}
      We need to only submit listens which were played in the past.
      */
      return "";
    }
  };
  
  trackMBID() {
    if ('mbid' in this.rootScrobbleElement) {
      return this.rootScrobbleElement['mbid'];
    } else {
      return "";
    }
  };
  
  asJSONSerializable() {
    let trackjson = {
      "track_metadata": {
        "track_name": this.trackName(),
        "artist_name": this.artistName(),
        "release_name": this.releaseName(),
        "additional_info": {
          "recording_mbid": this.trackMBID()
        }
      },
      "listened_at": this.scrobbledAt(),
    };
    
    // Remove keys with blank values
    (function filter(obj) {
      $.each(obj, function(key, value){
        if (value === "" || value === null){
          delete obj[key];
        } else if (Object.prototype.toString.call(value) === '[object Object]') {
          filter(value);
        } else if (Array.isArray(value)) {
          value.forEach(function (el) { filter(el); });
        }
      });
    })(trackjson);
    return trackjson;
  };
}

export default class Importer {  
  constructor(lastfmUsername, props, updateMessage, setClose) {
    this.APIService = new APIService(props.api_url || `${window.location.origin}/1`) // Used to access LB API
    
    this.updateMessage = updateMessage // Used to update the message in modal
    this.setClose = setClose; // Used to enable or disable close button in modal
    
    this.lastfmUsername = lastfmUsername;
    this.lastfmURL = props.lastfm_api_url;
    this.lastfmKey = props.lastfm_api_key;
    
    this.userName = props.user.name;
    this.userToken = props.user.auth_token;
    
    this.page = 1;
    this.totalPages = 0;
    this.playCount = -1; // the number of scrobbles reported by Last.FM
    this.countReceived = 0; // number of scrobbles the Last.FM API sends us, this can be diff from playCount
    
    this.submitQueue = []; // Queue that keeps tracks of submits to be made to LB
    this.isSubmitActive = false;
    
    this.latestImportTime = 0; // the latest timestamp that we've imported earlier
    this.maximumTimestampForImport = 0; // the latest listen found in this import
    this.incrementalImport = false;
    
    this.activeFetches = 0;
    this.maxActiveFetches = 10;
    
    this.timesGetPage = 0;
    this.timesReportScrobbles = 0;
    this.times4Error = 0;
    this.times5Error = 0;
    
    this.numCompleted = 0; // number of pages completed till now

    this.props = props;
  }
  
  async startImport() {
    this.setClose(false); // Disable the close button
    this.updateMessage("Your import from Last.fm is starting!");
    this.playCount = await this.getTotalNumberOfScrobbles();
    this.latestImportTime = await this.APIService.getLatestImport(this.userName); // TODO: Error handling, test usernames having special characters
    this.incrementalImport = this.latestImportTime > 0;
    this.totalPages = await this.getNumberOfPages();
    if (this.totalPages > 0) {
      this.getNextPagesIfSlots();
    }
    // Update latest import time on LB server
    this.APIService.setLatestImport(this.props.user.auth_token, this.maximumTimestampForImport);
    this.updateMessage("Done");
    this.setClose(true);
  }
  
  async getTotalNumberOfScrobbles() {
    /*
    * Get the total play count reported by Last.FM for user
    */
    
    let url = `${this.lastfmURL}?method=user.getinfo&user=${this.lastfmUsername}&api_key=${this.lastfmKey}&format=json`;
    try {
      let response = await fetch(encodeURI(url));
      let data = await response.json();
      if ('playcount' in data['user']) {
        return parseInt(data['user']['playcount']);
      } else {
        return -1;
      }
    } catch {
      this.updateMessage("An error occurred, please try again. :(")
      this.setClose(true); // Enable the close button
      return -1;
    }
  }
  
  async getNumberOfPages() {
    /*
    * Get the total pages of data from last import
    */
    
    let url = `${this.lastfmURL}?method=user.getrecenttracks&user=${this.lastfmUsername}&api_key=${this.lastfmKey}&from=${this.latestImportTime+1}&format=json`;
    try {
      let response = await fetch(encodeURI(url));
      let data = await response.json();
      if ('recenttracks' in data) {
        return parseInt(data['recenttracks']['@attr']['totalPages']);
      } else {
        return 0;
      }
    } catch {
      this.updateMessage("An error occurred, please try again. :(")
      this.setClose(true); // Enable the close button
      return 0;
    }
  }
  
  getNextPagesIfSlots() {
    /* 
    * Get next page if number of active fetches is less than 10 
    */
    
    while (this.activeFetches < this.maxActiveFetches && this.page < this.totalPages) {
      this.activeFetches++;
      this.getPage(this.page);
      this.page++;
    }
  }
  
  async getPage(page) {
    /*
    * Fetch page from Last.fm
    */ 
    
    let retry = (reason) => {
      console.warn(reason + ' fetching last.fm page=' + page + ', retrying in 3s');
      setTimeout(() => this.getPage(page), 3000);
    }
    
    let url = `${this.lastfmURL}?method=user.getrecenttracks&user=${this.lastfmUsername}&api_key=${this.lastfmKey}&from=${this.latestImportTime+1}&page=${page}&format=json`;
    try {
      let response = await fetch(encodeURI(url));
      if (response.ok) {
        let data = await response.json();
        // Set latest import time
        if (page === 1) {
          if ('date' in data['recenttracks']['track'][0]) {
            this.maximumTimestampForImport = data['recenttracks']['track'][0]['date']['uts'];
          } else {
            this.maximumTimestampForImport = Math.floor(Date.now() / 1000);
          }
        }
        this.reportPageAndGetNext(data, page);
      } else {
        if (/^5/.test(response.status)) {
          retry('got ' + response.status);
        } else {
          // ignore 40x
          this.pageDone()
        }
      }
    } catch {
      // Retry if there is a network error
      retry('error');
    }
  }
  
  reportPageAndGetNext(data, page) {
    this.timesGetPage++;
    if (page == 1) {
      this.updateMessage("Todo");
    }
    let payload = this.encodeScrobbles(data);
    this.submitQueue.push(payload);
    this.countReceived += payload.length;
    if (payload.length === 0) { 
      this.pageDone();
    } else {
      if (!this.isSubmitActive){
        this.isSubmitActive = true;
        this.submitListens();
      }
    }
    this.getNextPagesIfSlots();
  }
  
  pageDone() {
    this.activeFetches--;
    this.numCompleted++;
    
    // start the next submission
    if (this.submitQueue.length > 0) {
      this.submitListens();
    } else {
      this.isSubmitActive = false;
    }
    
    // Check to see if we need to start up more fetches
    this.getNextPagesIfSlots();    
  }
  
  async submitListens() {
    
    let payload = this.submitQueue.shift();

    try {
      this.timesReportScrobbles++;
      let status = await this.APIService.submitListens(this.props.user.auth_token, "import", payload);
      if (status >= 200 && status < 300) {
        this.pageDone();
      } else if (status == 429) {
        // This should never happen, but if it does, toss it back in and try again.
        this.submitQueue.unshift(payload);
        setTimeout(() => this.submitListens(), 3000);
      } else if (status >= 400 && status < 500) {
        this.times4Error++;
        // We mark 4xx errors as completed because we don't
        // retry them
        console.warn("4xx error, skipping");
        this.pageDone();
      } else if (status >= 500) {
        console.warn("received http error " + status + " req'ing");
        this.times5Error++;
        // If something causes a 500 error, better not repeat it and just skip it.
        this.pageDone();
      } else {
        console.warn("received http status " + status + ", skipping");
        this.pageDone();
      }
      
      this.updateMessage("Submit Listens");
      //   var msg = "<i class='fa fa-cog fa-spin'></i> Sending page " + numCompleted;
      
      //   // show total number of pages if this is the first import and not an incremental
      //   // import
      //   if (!incrementalImport) {
      //     msg += " of " + numberOfPages;
      //   }
      
      //   msg += " to ListenBrainz.<br><span style='font-size:8pt'>";
      
      //   // show a message explaining that this is an incremental import
      //   if (incrementalImport) {
      //     msg += "Note: This import will stop at the starting point of your last import. :)<br>";
      //   }
      
      //   msg += "Please don't close this page while this is running</span>"
      //   updateMessage(msg);
      
      // };
    } catch {
      console.warn("Error, retrying in 3s");
      this.submitQueue.unshift(payload);
      setTimeout(() => this.submitListens(), 3000);
    }
  }
  
  encodeScrobbles(scrobbles) {
    scrobbles = scrobbles['recenttracks']['track'];
    let parsedScrobbles = this.map((rawScrobble) => {
      let scrobble = new Scrobble(rawScrobble);
      return scrobble.asJSONSerializable();
    }, scrobbles);
    return parsedScrobbles;
  }
  
  map(applicable, collection) {
    let newCollection = [];
    for (let i = 0; i < collection.length; i++) {
      let result = applicable(collection[i]);
      if ('listened_at' in result) {
        // Add If there is no 'listened_at' attribute then either the listen is invalid or the
        // listen is currently playing. In both cases we need to skip the submission.
        newCollection.push(result);
      };
    }
    return newCollection;
  }
}
