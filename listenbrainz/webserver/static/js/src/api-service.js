// TODO: Make the code ESLint compliant
// TODO: Port to typescript

import { isFinite, isNil, isString } from "lodash";

export default class APIService {
  APIBaseURI;

  constructor(APIBaseURI) {
    if (isNil(APIBaseURI) || !isString(APIBaseURI)) {
      throw new SyntaxError(
        `Expected API base URI string, got ${typeof APIBaseURI} instead`
      );
    }
    if (APIBaseURI.endsWith("/")) {
      APIBaseURI = APIBaseURI.substring(0, APIBaseURI.length - 1);
    }
    if (!APIBaseURI.endsWith("/1")) {
      APIBaseURI += "/1";
    }
    this.APIBaseURI = APIBaseURI;
    this.MAX_LISTEN_SIZE = 10000; // Maximum size of listens that can be sent
  }

  async getRecentListensForUsers(userNames, limit) {
    let userNamesForQuery = userNames;
    if (Array.isArray(userNames)) {
      userNamesForQuery = userNames.join(",");
    } else if (typeof userNames !== "string") {
      throw new SyntaxError(
        `Expected username or array of username strings, got ${typeof userNames} instead`
      );
    }

    let query = `${this.APIBaseURI}/users/${userNamesForQuery}/recent-listens`;

    if (!isNil(limit) && isFinite(Number(limit))) {
      query += `?limit=${limit}`;
    }

    const response = await fetch(query, {
      accept: "application/json",
      method: "GET",
    });
    this.checkStatus(response);
    const result = await response.json();

    return result.payload.listens;
  }

  async getListensForUser(userName, minTs, maxTs, count) {
    if (typeof userName !== "string") {
      throw new SyntaxError(
        `Expected username string, got ${typeof userName} instead`
      );
    }
    if (!isNil(maxTs) && !isNil(minTs)) {
      throw new SyntaxError(
        "Cannot have both minTs and maxTs defined at the same time"
      );
    }

    let query = `${this.APIBaseURI}/user/${userName}/listens`;

    const queryParams = [];
    if (!isNil(maxTs) && isFinite(Number(maxTs))) {
      queryParams.push(`max_ts=${maxTs}`);
    }
    if (!isNil(minTs) && isFinite(Number(minTs))) {
      queryParams.push(`min_ts=${minTs}`);
    }
    if (!isNil(count) && isFinite(Number(count))) {
      queryParams.push(`count=${count}`);
    }
    if (queryParams.length) {
      query += `?${queryParams.join("&")}`;
    }

    const response = await fetch(query, {
      accept: "application/json",
      method: "GET",
    });
    this.checkStatus(response);
    const result = await response.json();

    return result.payload.listens;
  }

  async refreshSpotifyToken() {
    const response = await fetch("/profile/refresh-spotify-token", {
      method: "POST",
    });
    this.checkStatus(response);
    const result = await response.json();
    return result.user_token;
  }

  async submitListens(userToken, listenType, payload) {
    /*
      Send a POST request to the ListenBrainz server to submit a listen
    */

    if (!isString(userToken)) {
      throw new SyntaxError(
        `Expected usertoken string, got ${typeof userToken} instead`
      );
    }
    if (
      listenType !== "single" &&
      listenType !== "playingNow" &&
      listenType !== "import"
    ) {
      throw new SyntaxError(
        `listenType can be "single", "playingNow" or "import", got ${listenType} instead`
      );
    }

    if (JSON.stringify(payload).length <= this.MAX_LISTEN_SIZE) {
      // Payload is within submission limit, submit directly
      const struct = {
        listen_type: listenType,
        payload,
      };

      const url = `${this.APIBaseURI}/submit-listens`;

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            Authorization: `Token ${userToken}`,
            "Content-Type": "application/json;charset=UTF-8",
          },
          body: JSON.stringify(struct),
        });

        if (response.status == 429) {
          // This should never happen, but if it does, try again.
          console.warn("Error, retrying in 3 sec");
          setTimeout(
            () => this.submitListens(userToken, listenType, payload),
            3000
          );
        } else if (!(response.status >= 200 && response.status < 300)) {
          console.warn(`Got ${response.status} error, skipping`);
        }
        return response; // Return response so that caller can handle appropriately
      } catch {
        // Retry if there is an network error
        console.warn("Error, retrying in 3 sec");
        setTimeout(
          () => this.submitListens(userToken, listenType, payload),
          3000
        );
      }
    } else {
      // Payload is not within submission limit, split and submit
      await this.submitListens(
        userToken,
        listenType,
        payload.slice(0, payload.length / 2)
      );
      return await this.submitListens(
        userToken,
        listenType,
        payload.slice(payload.length / 2, payload.length)
      );
    }
  }

  async getLatestImport(userName) {
    /*
     *  Send a GET request to the ListenBrainz server to get the latest import time
     *  from previous imports for the user.
     */

    if (!isString(userName)) {
      throw new SyntaxError(
        `Expected username string, got ${typeof userName} instead`
      );
    }
    let url = `${this.APIBaseURI}/latest-import?user_name=${userName}`;
    url = encodeURI(url);
    const response = await fetch(url, {
      method: "GET",
    });
    this.checkStatus(response);
    const result = await response.json();
    return parseInt(result.latest_import);
  }

  async setLatestImport(userToken, timestamp) {
    /*
     * Send a POST request to the ListenBrainz server after the import is complete to
     * update the latest import time on the server. This will make future imports stop
     * when they reach this point of time in the listen history.
     */

    if (!isString(userToken)) {
      throw new SyntaxError(
        `Expected usertoken string, got ${typeof userToken} instead`
      );
    }
    if (!isFinite(timestamp)) {
      throw new SyntaxError(
        `Expected timestamp number, got ${typeof timestamp} instead`
      );
    }

    const url = `${this.APIBaseURI}/latest-import`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ ts: parseInt(timestamp) }),
    });
    this.checkStatus(response);
    return response.status; // Return true if timestamp is updated
  }

  checkStatus(response) {
    if (response.status >= 200 && response.status < 300) {
      return;
    }
    const error = new Error(`HTTP Error ${response.statusText}`);
    error.status = response.statusText;
    error.response = response;
    throw error;
  }
}
