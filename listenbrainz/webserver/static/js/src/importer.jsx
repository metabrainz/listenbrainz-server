/* eslint-disable */
// TODO: Make the code ESLint compliant
// TODO: Port to typescript

import React from "react";
import { faSpinner, faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Scrobble from "./scrobble";
import APIService from "./api-service";

export default class Importer {
  constructor(lastfmUsername, props) {
    this.APIService = new APIService(
      props.api_url || `${window.location.origin}/1`
    ); // Used to access LB API

    this.lastfmUsername = lastfmUsername;
    this.lastfmURL = props.lastfm_api_url;
    this.lastfmKey = props.lastfm_api_key;

    this.userName = props.user.name;
    this.userToken = props.user.auth_token;

    this.page = 1;
    this.totalPages = 0;
    this.playCount = -1; // the number of scrobbles reported by Last.FM
    this.countReceived = 0; // number of scrobbles the Last.FM API sends us, this can be diff from playCount

    this.latestImportTime = 0; // the latest timestamp that we've imported earlier
    this.maxTimestampForImport = 0; // the latest listen found in this import
    this.incrementalImport = false;

    this.numCompleted = 0; // number of pages completed till now

    this.props = props;

    // Variables used to honor LB's rate limit
    this.rl_remain = -1;
    this.rl_reset = -1;
    this.rl_origin = -1;

    // Message to be outputed in modal
    this.msg = "";
    this.canClose = true;
  }

  async startImport() {
    this.canClose = false; // Disable the close button
    this.updateMessage("Your import from Last.fm is starting!");
    this.playCount = await this.getTotalNumberOfScrobbles();
    this.latestImportTime = await this.APIService.getLatestImport(
      this.userName
    );
    this.incrementalImport = this.latestImportTime > 0;
    this.totalPages = await this.getNumberOfPages();
    this.page = this.totalPages; // Start from the last page so that oldest scrobbles are imported first

    while (this.page > 0) {
      const payload = await this.getPage(this.page);
      if (payload) {
        // Submit only if response is valid
        this.submitPage(payload);
      }

      this.page--;
      this.numCompleted++;

      // Update message
      const msg = (
        <p>
          <FontAwesomeIcon icon={faSpinner} spin /> Sending page{" "}
          {this.numCompleted} of {this.totalPages} to ListenBrainz <br />
          <span style={{ fontSize: `${8}pt` }}>
            {this.incrementalImport && (
              <span>
                Note: This import will stop at the starting point of your last
                import. :)
                <br />
              </span>
            )}
            <span>Please don't close this page while this is running</span>
          </span>
        </p>
      );
      this.updateMessage(msg);
    }

    // Update latest import time on LB server
    try {
      this.maxTimestampForImport = Math.max(
        parseInt(this.maxTimestampForImport),
        this.latestImportTime
      );
      this.APIService.setLatestImport(
        this.userToken,
        this.maxTimestampForImport
      );
    } catch {
      console.warn("Error, retrying in 3s");
      setTimeout(
        () =>
          this.APIService.setLatestImport(
            this.userToken,
            this.maxTimestampForImport
          ),
        3000
      );
    }
    const final_msg = (
      <p>
        <FontAwesomeIcon icon={faCheck} /> Import finished
        <br />
        <span style={{ fontSize: `${8}pt` }}>
          Successfully submitted {this.countReceived} listens to ListenBrainz
          <br />
        </span>
        {/* if the count received is different from the api count, show a message accordingly
         * also don't show this message if it's an incremental import, because countReceived
         * and playCount will be different by definition in incremental imports
         */}
        {!this.incrementalImport &&
          this.playCount != -1 &&
          this.countReceived != this.playCount && (
            <b>
              <span style={{ fontSize: `${10}pt` }} className="text-danger">
                The number submitted listens is different from the{" "}
                {this.playCount} that Last.fm reports due to an inconsistency in
                their API, sorry!
                <br />
              </span>
            </b>
          )}
        <span style={{ fontSize: `${8}pt` }}>
          Thank you for using ListenBrainz!
        </span>
        <br />
        <br />
        <span style={{ fontSize: `${10}pt` }}>
          <a href={`${this.props.profile_url}`}>
            Close and go to your ListenBrainz profile
          </a>
        </span>
      </p>
    );
    this.updateMessage(final_msg);
    this.canClose = true;
  }

  async getTotalNumberOfScrobbles() {
    /*
     * Get the total play count reported by Last.FM for user
     */

    const url = `${this.lastfmURL}?method=user.getinfo&user=${this.lastfmUsername}&api_key=${this.lastfmKey}&format=json`;
    try {
      const response = await fetch(encodeURI(url));
      const data = await response.json();
      if ("playcount" in data.user) {
        return parseInt(data.user.playcount);
      }
      return -1;
    } catch {
      this.updateMessage("An error occurred, please try again. :(");
      this.canClose = true; // Enable the close button
      error = new Error();
      error.message = "Something went wrong";
      throw error;
    }
  }

  async getNumberOfPages() {
    /*
     * Get the total pages of data from last import
     */

    const url = `${this.lastfmURL}?method=user.getrecenttracks&user=${
      this.lastfmUsername
    }&api_key=${this.lastfmKey}&from=${this.latestImportTime + 1}&format=json`;
    try {
      const response = await fetch(encodeURI(url));
      const data = await response.json();
      if ("recenttracks" in data) {
        return parseInt(data.recenttracks["@attr"].totalPages);
      }
      return 0;
    } catch (error) {
      this.updateMessage("An error occurred, please try again. :(");
      this.canClose = true; // Enable the close button
      return -1;
    }
  }

  async getPage(page) {
    /*
     * Fetch page from Last.fm
     */

    const retry = (reason) => {
      console.warn(`${reason} fetching last.fm page=${page}, retrying in 3s`);
      setTimeout(() => this.getPage(page), 3000);
    };

    const url = `${this.lastfmURL}?method=user.getrecenttracks&user=${
      this.lastfmUsername
    }&api_key=${this.lastfmKey}&from=${
      this.latestImportTime + 1
    }&page=${page}&format=json`;
    try {
      const response = await fetch(encodeURI(url));
      if (response.ok) {
        const data = await response.json();
        // Set latest import time
        if ("date" in data.recenttracks.track[0]) {
          this.maxTimestampForImport = Math.max(
            data.recenttracks.track[0].date.uts,
            this.maxTimestampForImport
          );
        } else {
          this.maxTimestampForImport = Math.floor(Date.now() / 1000);
        }

        // Encode the page so that it can be submitted
        const payload = this.encodeScrobbles(data);
        this.countReceived += payload.length;
        return payload;
      }
      if (/^5/.test(response.status)) {
        retry(`Got ${response.status}`);
      } else {
        // ignore 40x
        console.warn(`Got ${response.status}, skipping`);
      }
    } catch {
      // Retry if there is a network error
      retry("Error");
    }
  }

  async submitPage(payload) {
    const delay = this.getRateLimitDelay();
    // Halt execution for some time
    await new Promise((resolve) => {
      setTimeout(resolve, delay);
    });

    const response = await this.APIService.submitListens(
      this.userToken,
      "import",
      payload
    );
    this.updateRateLimitParameters(response);
  }

  encodeScrobbles(scrobbles) {
    scrobbles = scrobbles.recenttracks.track;
    const parsedScrobbles = this.map((rawScrobble) => {
      const scrobble = new Scrobble(rawScrobble);
      return scrobble.asJSONSerializable();
    }, scrobbles);
    return parsedScrobbles;
  }

  map(applicable, collection) {
    const newCollection = [];
    for (let i = 0; i < collection.length; i++) {
      const result = applicable(collection[i]);
      if ("listened_at" in result) {
        // Add If there is no 'listened_at' attribute then either the listen is invalid or the
        // listen is currently playing. In both cases we need to skip the submission.
        newCollection.push(result);
      }
    }
    return newCollection;
  }

  updateMessage = (msg) => {
    this.msg = msg;
  };

  getRateLimitDelay() {
    /* Get the amount of time we should wait according to LB rate limits before making a request to LB */
    let delay = 0;
    const current = new Date().getTime() / 1000;
    if (this.rl_reset < 0 || current > this.rl_origin + this.rl_reset) {
      delay = 0;
    } else if (this.rl_remain > 0) {
      delay = Math.max(0, Math.ceil((this.rl_reset * 1000) / this.rl_remain));
    } else {
      delay = Math.max(0, Math.ceil(this.rl_reset * 1000));
    }
    return delay;
  }

  updateRateLimitParameters(response) {
    /* Update the variables we use to honor LB's rate limits */
    this.rl_remain = parseInt(response.headers.get("X-RateLimit-Remaining"));
    this.rl_reset = parseInt(response.headers.get("X-RateLimit-Reset-In"));
    this.rl_origin = new Date().getTime() / 1000;
  }
}
