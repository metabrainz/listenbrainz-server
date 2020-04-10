import APIError from "./APIError";
import { Listen, SubmitListensPayload, ListenType } from "./types"; // eslint-disable-line no-unused-vars

export default class APIService {
  APIBaseURI: string;

  MAX_LISTEN_SIZE: number = 10000; // Maximum size of listens that can be sent

  constructor(APIBaseURI: string) {
    let finalUri = APIBaseURI;
    if (finalUri.endsWith("/")) {
      finalUri = finalUri.substring(0, APIBaseURI.length - 1);
    }
    if (!finalUri.endsWith("/1")) {
      finalUri += "/1";
    }
    this.APIBaseURI = finalUri;
  }

  getRecentListensForUsers = async (
    userNames: Array<string>,
    limit?: number
  ): Promise<Array<Listen>> => {
    const userNamesForQuery: string = userNames.join(",");

    let query = `${this.APIBaseURI}/users/${userNamesForQuery}/recent-listens`;

    if (limit) {
      query += `?limit=${limit}`;
    }

    const response = await fetch(query, {
      method: "GET",
    });
    this.checkStatus(response);
    const result = await response.json();

    return result.payload.listens;
  };

  getListensForUser = async (
    userName: string,
    minTs?: number,
    maxTs?: number,
    count?: number
  ): Promise<Array<Listen>> => {
    if (maxTs && minTs) {
      throw new SyntaxError(
        "Cannot have both minTs and maxTs defined at the same time"
      );
    }

    let query: string = `${this.APIBaseURI}/user/${userName}/listens`;

    const queryParams: Array<string> = [];
    if (maxTs) {
      queryParams.push(`max_ts=${maxTs}`);
    }
    if (minTs) {
      queryParams.push(`min_ts=${minTs}`);
    }
    if (count) {
      queryParams.push(`count=${count}`);
    }
    if (queryParams.length) {
      query += `?${queryParams.join("&")}`;
    }

    const response = await fetch(query, {
      method: "GET",
    });
    this.checkStatus(response);
    const result = await response.json();

    return result.payload.listens;
  };

  refreshSpotifyToken = async (): Promise<string> => {
    const response = await fetch("/profile/refresh-spotify-token", {
      method: "POST",
    });
    this.checkStatus(response);
    const result = await response.json();
    return result.user_token;
  };

  /*
    Send a POST request to the ListenBrainz server to submit a listen
  */
  submitListens = async (
    userToken: string,
    listenType: ListenType,
    payload: SubmitListensPayload
  ): Promise<Response> => {
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

        // we skip listens if we get an error code that's not a rate limit
        if (response.status === 429) {
          // Rate limit error, this should never happen, but if it does, try again in 3 seconds.
          setTimeout(
            () => this.submitListens(userToken, listenType, payload),
            3000
          );
        }
        return response; // Return response so that caller can handle appropriately
      } catch {
        // Retry if there is an network error
        setTimeout(
          () => this.submitListens(userToken, listenType, payload),
          3000
        );
      }
    }

    // Payload is not within submission limit, split and submit
    await this.submitListens(
      userToken,
      listenType,
      payload.slice(0, payload.length / 2)
    );
    return this.submitListens(
      userToken,
      listenType,
      payload.slice(payload.length / 2, payload.length)
    );
  };

  /*
   *  Send a GET request to the ListenBrainz server to get the latest import time
   *  from previous imports for the user.
   */
  getLatestImport = async (userName: string): Promise<number> => {
    const url = encodeURI(
      `${this.APIBaseURI}/latest-import?user_name=${userName}`
    );
    const response = await fetch(url, {
      method: "GET",
    });
    this.checkStatus(response);
    const result = await response.json();
    return parseInt(result.latest_import, 10);
  };

  /*
   * Send a POST request to the ListenBrainz server after the import is complete to
   * update the latest import time on the server. This will make future imports stop
   * when they reach this point of time in the listen history.
   */
  setLatestImport = async (
    userToken: string,
    timestamp: string
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/latest-import`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ ts: parseInt(timestamp, 10) }),
    });
    this.checkStatus(response);
    return response.status; // Return true if timestamp is updated
  };

  checkStatus = (response: Response): void => {
    if (response.status >= 200 && response.status < 300) {
      return;
    }
    const error = new APIError(`HTTP Error ${response.statusText}`);
    error.status = response.statusText;
    error.response = response;
    throw error;
  };
}
