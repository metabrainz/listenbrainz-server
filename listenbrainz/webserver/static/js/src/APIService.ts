import APIError from "./APIError";

const data = {
  payload: {
    artists: [
      {
        artist_mbids: [],
        artist_msid: "d340853d-7408-4a0d-89c2-6ff13e568815",
        artist_name: "The Local train",
        listen_count: 385,
      },
      {
        artist_mbids: [],
        artist_msid: "ba64b195-01dd-4613-9534-bb87dc44cffb",
        artist_name: "Lenka",
        listen_count: 333,
      },
      {
        artist_mbids: [],
        artist_msid: "6599e41e-390c-4855-a2ac-68ee798538b4",
        artist_name: "Coldplay",
        listen_count: 321,
      },
      {
        artist_mbids: [],
        artist_msid: "fecda98e-0533-4b87-a9d1-c89b4521918b",
        artist_name: "Imagine Dragons",
        listen_count: 176,
      },
      {
        artist_mbids: [],
        artist_msid: "9d5adabb-9775-4535-93eb-12b485aed8bf",
        artist_name: "Maroon 5",
        listen_count: 118,
      },
      {
        artist_mbids: [],
        artist_msid: "7addbcac-ae39-4b4c-a956-53da336d68e8",
        artist_name: "Ellie Goulding",
        listen_count: 108,
      },
      {
        artist_mbids: [],
        artist_msid: "67f4ae2e-260e-4020-b957-f2df5b719501",
        artist_name: "OneRepublic",
        listen_count: 65,
      },
      {
        artist_mbids: [],
        artist_msid: "2b0646af-f3f0-4a5b-b629-6c31301c1c29",
        artist_name: "The Weeknd",
        listen_count: 52,
      },
      {
        artist_mbids: [],
        artist_msid: "0daecabb-f76d-4914-8726-82cefbecca52",
        artist_name: "The Chainsmokers",
        listen_count: 44,
      },
      {
        artist_mbids: [],
        artist_msid: "3b155259-b29e-4515-aa62-cb0b917f4cfd",
        artist_name: "The Fray",
        listen_count: 41,
      },
      {
        artist_mbids: [],
        artist_msid: "52f911d4-8f73-4fc9-9145-a99aff057524",
        artist_name: "George Ezra",
        listen_count: 35,
      },
      {
        artist_mbids: [],
        artist_msid: "cc0f643d-cba9-4a5e-876f-cb3d70cdf5ea",
        artist_name: "Taylor Swift",
        listen_count: 34,
      },
      {
        artist_mbids: [],
        artist_msid: "fbe59c7e-3a75-459b-8fc8-07abaa6d1d2c",
        artist_name: "Train",
        listen_count: 34,
      },
      {
        artist_mbids: [],
        artist_msid: "1024e884-3a17-4729-9e59-a026fe8a07ba",
        artist_name: "M.I.A.",
        listen_count: 33,
      },
      {
        artist_mbids: [],
        artist_msid: "0c115c8a-fc71-4649-aa75-aaef5f09d6d1",
        artist_name: "American Authors",
        listen_count: 30,
      },
      {
        artist_mbids: [],
        artist_msid: "4e202a9c-c976-4e9e-8c9f-b0b96916f6a5",
        artist_name: "Tommee Profitt",
        listen_count: 30,
      },
      {
        artist_mbids: [],
        artist_msid: "50751cf3-40c6-454e-99d9-3d5777e4ad4f",
        artist_name: "Within Temptation",
        listen_count: 30,
      },
    ],
  },
};

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
    payload: Array<Listen>
  ): Promise<Response> => {
    if (JSON.stringify(payload).length <= this.MAX_LISTEN_SIZE) {
      // Payload is within submission limit, submit directly
      const struct = {
        listen_type: listenType,
        payload,
      } as SubmitListensPayload;

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
    timestamp: number
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/latest-import`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ ts: timestamp }),
    });
    this.checkStatus(response);
    return response.status; // Return true if timestamp is updated
  };

  getUserStats = async (
    userName: string,
    range: "all_time" = "all_time",
    offset: number = 0,
    count?: number
  ): Promise<any> => {
    return Promise.resolve(data);
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
