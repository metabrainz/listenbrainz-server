import APIService from './api-service'

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
    this.numberOfPages = 0;
    this.playCount = -1; // the number of scrobbles reported by Last.FM
    this.countReceived = 0; // number of scrobbles the Last.FM API sends us, this can be diff from playCount
    
    this.submitQueue = []; // Queue that keeps tracks of submits to be made to LB
    this.isSubmitActive = false;
    
    this.latestImportTime = 0; // the latest timestamp that we've imported earlier
    this.maximumTimestampForImport = 0; // the latest listen found in this import
    this.incrementalImport = false;
    
    this.activeFetches = 0;
    this.maxActiveFetches = 10;
  }

  async startImport() {
    this.setClose(false); // Disable the close button
    this.updateMessage("Your import from Last.fm is starting!");
    this.playCount = await this.getTotalNumberOfScrobbles();
    this.latestImportTime = await this.APIService.getLatestImport(this.userName); // TODO: Error handling, test usernames having special characters
    this.incrementalImport = this.latestImportTime > 0;
    this.numberOfPages = await this.getNumberOfPages();
    if (this.numberOfPages > 0) {
      this.getNextPageIfSlot();
    }
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

  getNextPageIfSlot() {
    /* 
     * Get next page if number of active fetches is less than 10 
     */

    while (this.activeFetches < this.maxActiveFetches) {
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
      setTimeout(this.getPage(page), 3000);
    }

    let url = `${this.lastfmURL}?method=user.getrecenttracks&user=${this.lastfmUsername}&api_key=${this.lastfmKey}&from=${this.latestImportTime+1}&page=${page}&format=json`;
    try {
      let response = await fetch(encodeURI(url));
      if (response.ok) {
        let data = await response.json();
        // TODO
      } else {
        if (/^5/.test(response.status)) {
          retry('got ' + response.status);
        } else {
          // ignore 40x
          // TODO
        }
      }
    } catch {
      // Retry if there is a network error
      retry('error');
    }
  }
}
