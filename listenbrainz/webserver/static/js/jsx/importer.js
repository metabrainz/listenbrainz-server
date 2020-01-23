import APIService from './api-service'
import React from 'react';
import { faSpinner, faCheck } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

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

    this.activeSubmits = 0;
    this.maxActiveSubmits = 10;

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
      await this.getListens();
    }
    if (this.submitQueue.length > 0) {
      await this.submitListens();
    }
    // Update latest import time on LB server
    try {
      this.maximumTimestampForImport = Math.max(parseInt(this.maximumTimestampForImport), this.latestImportTime);
      this.APIService.setLatestImport(this.userToken, this.maximumTimestampForImport);
    } catch {
      console.warn("Error, retrying in 3s");
      setTimeout(() => this.APIService.setLatestImport(this.userToken, this.maximumTimestampForImport), 3000)
    }
    let final_msg = (
      <p>
        <FontAwesomeIcon icon={faCheck}/> Import finished<br/>
        <span style={{fontSize: 8+'pt'}}>Successfully submitted {this.countReceived} listens to ListenBrainz<br/></span>
        {/* if the count received is different from the api count, show a message accordingly
          * also don't show this message if it's an incremental import, because countReceived
          * and playCount will be different by definition in incremental imports
        */}
        {!this.incrementalImport && this.playCount != -1 && this.countReceived != this.playCount &&
          <b><span style={{fontSize: 10+'pt'}} className="text-danger">The number submitted listens is different from the {this.playCount} that Last.fm reports due to an inconsistency in their API, sorry!<br/></span></b>
        }
        <span style={{fontSize: 8+'pt'}}>Thank you for using ListenBrainz!</span>
        {/* For debugging} */}
        <span style={{display:'none'}}>
          reportedScrobbles = {this.timesReportScrobbles} <br/>
          getPage = {this.timesGetPage} <br/>
          number4xx = {this.imes4Error} <br/>
          number5xx = {this.times5Error} <br/>
          page = {this.page} <br/>
        </span> 
      </p>
    );
    this.updateMessage(final_msg);
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
    } catch(error) {
      this.updateMessage("An error occurred, please try again. :(")
      this.setClose(true); // Enable the close button
      throw error;
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
    } catch(error) {
      this.updateMessage("An error occurred, please try again. :(")
      this.setClose(true); // Enable the close button
      console.log(error);
    }
  }

  getListens() {
    this.getNextPagesIfSlots();

    return new Promise((resolve, reject) => {
      // Resolve the promise if number of pages recieved is equal to total pages
      let that = this;
      (function waitForPages(){
        if (that.timesGetPage == that.totalPages) 
          return resolve();
        setTimeout(waitForPages, 100);
      })();
    })
  }

  getNextPagesIfSlots() {
    /*
    * Get next page if number of active fetches is less than 10
    */

    while (this.activeFetches < this.maxActiveFetches && this.page <= this.totalPages) {
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
        this.reportPageAndGetNext(data);
      } else {
        if (/^5/.test(response.status)) {
          retry('got ' + response.status);
        } else {
          // ignore 40x
          this.pageGetDone()
        }
      }
    } catch {
      // Retry if there is a network error
      retry('error');
    }
  }

  reportPageAndGetNext(data) {
    let payload = this.encodeScrobbles(data);
    this.submitQueue.push(payload);
    this.countReceived += payload.length;
    this.pageGetDone();
  }

  pageGetDone() {
    this.activeFetches--;
    this.timesGetPage++;
    this.updateMessage(<p><FontAwesomeIcon icon={faSpinner} spin/> Getting page {this.timesGetPage} of {this.totalPages}<br/><span style={{fontSize: 8+'pt'}}>Please do not close this page while the process is running</span></p>);
    // Check to see if we need to start up more fetches
    this.getNextPagesIfSlots();
  }

  submitListens() {
    this.submitNextPagesIfSlots();

    return new Promise((resolve, reject) => {
      // Resolve the promise if number of pages recieved is equal to total pages
      let that = this;
      (function waitForPages(){
        if (that.numCompleted == that.totalPages) 
          return resolve();
        setTimeout(waitForPages, 100);
      })();
    })
  }

  submitNextPagesIfSlots() {
    /*
    * Submit next page if number of active fetches is less than 10
    */

   while (this.activeSubmits < this.maxActiveSubmits && this.submitQueue.length) {
      this.activeSubmits++;
      let payload = this.submitQueue.shift();
      console.log(this.submitQueue);
      this.submitPage(payload);
    } 
  }

  async submitPage(payload) {
    try {
      this.timesReportScrobbles++;
      let status = await this.APIService.submitListens(this.userToken, "import", payload);
      if (status >= 200 && status < 300) {
        this.pageSubmitDone();
      } else if (status == 429) {
        // This should never happen, but if it does, toss it back in and try again.
        setTimeout(() => this.submitListens(payload), 3000);
      } else if (status >= 400 && status < 500) {
        this.times4Error++;
        // We mark 4xx errors as completed because we don't
        // retry them
        console.warn("4xx error, skipping");
        this.pageSubmitDone();
      } else if (status >= 500) {
        console.warn("received http error " + status + " req'ing");
        this.times5Error++;
        // If something causes a 500 error, better not repeat it and just skip it.
        this.pageSubmitDone();
      } else {
        console.warn("received http status " + status + ", skipping");
        this.pageSubmitDone();
      }
    } catch {
      console.warn("Error, retrying in 3s");
      setTimeout(() => this.submitListens(payload), 3000);
    }
  }

  pageSubmitDone() {
    this.numCompleted++;
    this.activeSubmits--;
    let msg = (
      <p>
      <FontAwesomeIcon icon={faSpinner} spin/> Sending page {this.numCompleted} of {this.totalPages} to ListenBrainz <br/>
      <span style={{fontSize:8+'pt'}}>
      {this.incrementalImport && <span>Note: This import will stop at the starting point of your last import. :)<br/></span>}
      <span>Please don't close this page while this is running</span>
      </span>
      </p>
    );
    this.updateMessage(msg);
    this.submitNextPagesIfSlots()
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
