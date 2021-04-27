import { isNil } from "lodash";
import APIError from "./APIError";

export default class APIService {
  APIBaseURI: string;

  MAX_LISTEN_SIZE: number = 10000; // Maximum size of listens that can be sent

  MAX_TIME_RANGE: number = 73;

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
    await this.checkStatus(response);
    const result = await response.json();

    return result.payload.listens;
  };

  getListensForUser = async (
    userName: string,
    minTs?: number,
    maxTs?: number,
    count?: number,
    timeRange?: number
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
    if (timeRange) {
      queryParams.push(`time_range=${timeRange}`);
    }
    if (queryParams.length) {
      query += `?${queryParams.join("&")}`;
    }

    const response = await fetch(query, {
      method: "GET",
    });
    await this.checkStatus(response);
    const result = await response.json();

    return result.payload.listens;
  };

  getUserListenCount = async (userName: string): Promise<number> => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }

    const query: string = `${this.APIBaseURI}/user/${userName}/listen-count`;

    const response = await fetch(query, {
      method: "GET",
    });
    await this.checkStatus(response);
    const result = await response.json();

    return parseInt(result.payload.count, 10);
  };

  refreshSpotifyToken = async (): Promise<string> => {
    const response = await fetch("/profile/refresh-spotify-token", {
      method: "POST",
    });
    await this.checkStatus(response);
    const result = await response.json();
    return result.user_token;
  };

  followUser = async (username: string): Promise<{ status: number }> => {
    const response = await fetch(`/user/${username}/follow`, {
      method: "POST",
    });
    return { status: response.status };
  };

  unfollowUser = async (username: string): Promise<{ status: number }> => {
    const response = await fetch(`/user/${username}/unfollow`, {
      method: "POST",
    });
    return { status: response.status };
  };

  getFollowersOfUser = async (username: string) => {
    if (!username) {
      throw new SyntaxError("Username missing");
    }

    const url = `/user/${username}/followers`;
    const response = await fetch(url);
    await this.checkStatus(response);
    const data = response.json();
    return data;
  };

  getFollowingForUser = async (username: string) => {
    if (!username) {
      throw new SyntaxError("Username missing");
    }

    const url = `/user/${username}/following`;
    const response = await fetch(url);
    await this.checkStatus(response);
    const data = response.json();
    return data;
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
    await this.checkStatus(response);
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
    await this.checkStatus(response);
    return response.status; // Return true if timestamp is updated
  };

  getUserEntity = async (
    userName: string,
    entity: Entity,
    range: UserStatsAPIRange = "all_time",
    offset: number = 0,
    count?: number
  ): Promise<UserEntityResponse> => {
    let url = `${this.APIBaseURI}/stats/user/${userName}/${entity}s?offset=${offset}&range=${range}`;
    if (count !== null && count !== undefined) {
      url += `&count=${count}`;
    }
    const response = await fetch(url);
    await this.checkStatus(response);
    // if response code is 204, then statistics havent been calculated, send empty object
    if (response.status === 204) {
      const error = new APIError(`HTTP Error ${response.statusText}`);
      error.status = response.statusText;
      error.response = response;
      throw error;
    }
    const data = response.json();
    return data;
  };

  getUserListeningActivity = async (
    userName: string,
    range: UserStatsAPIRange = "all_time"
  ): Promise<UserListeningActivityResponse> => {
    const url = `${this.APIBaseURI}/stats/user/${userName}/listening-activity?range=${range}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    if (response.status === 204) {
      const error = new APIError(`HTTP Error ${response.statusText}`);
      error.status = response.statusText;
      error.response = response;
      throw error;
    }
    const data = response.json();
    return data;
  };

  getUserDailyActivity = async (
    userName: string,
    range: UserStatsAPIRange = "all_time"
  ): Promise<UserDailyActivityResponse> => {
    const url = `${this.APIBaseURI}/stats/user/${userName}/daily-activity?range=${range}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    if (response.status === 204) {
      const error = new APIError(`HTTP Error ${response.statusText}`);
      error.status = response.statusText;
      error.response = response;
      throw error;
    }
    const data = response.json();
    return data;
  };

  getUserArtistMap = async (
    userName: string,
    range: UserStatsAPIRange = "all_time",
    forceRecalculate: boolean = false
  ) => {
    const url = `${this.APIBaseURI}/stats/user/${userName}/artist-map?range=${range}&force_recalculate=${forceRecalculate}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    if (response.status === 204) {
      const error = new APIError(`HTTP Error ${response.statusText}`);
      error.status = response.statusText;
      error.response = response;
      throw error;
    }
    const data = response.json();
    return data;
  };

  checkStatus = async (response: Response): Promise<void> => {
    if (response.status >= 200 && response.status < 300) {
      return;
    }
    const data = response.body || (response.json && (await response.json()));
    let message;
    if (data?.error) {
      message = data?.error;
    } else {
      message = `HTTP Error ${response.statusText}`;
    }
    const error = new APIError(`HTTP Error ${response.statusText}`);
    error.status = response.statusText;
    error.response = response;
    error.message = message;
    throw error;
  };

  getCoverArt = async (
    releaseMBID: string,
    recordingMSID: string
  ): Promise<string | null> => {
    const url = `${this.APIBaseURI}/get-cover-art/?release_mbid=${releaseMBID}&recording_msid=${recordingMSID}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    if (response.status === 200) {
      const data = await response.json();
      return data.image_url;
    }
    return null;
  };

  submitFeedback = async (
    userToken: string,
    recordingMSID: string,
    score: ListenFeedBack
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/feedback/recording-feedback`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ recording_msid: recordingMSID, score }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  getFeedbackForUserForRecordings = async (
    userName: string,
    recordings: string
  ) => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }

    const url = `${this.APIBaseURI}/feedback/user/${userName}/get-feedback-for-recordings?recordings=${recordings}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    const data = response.json();
    return data;
  };

  deleteListen = async (
    userToken: string,
    recordingMSID: string,
    listenedAt: number
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/delete-listen`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({
        listened_at: listenedAt,
        recording_msid: recordingMSID,
      }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  createPlaylist = async (
    userToken: string,
    playlistObject: JSPFObject
  ): Promise<string> => {
    if (!playlistObject.playlist?.title) {
      throw new SyntaxError("playlist title missing");
    }

    const url = `${this.APIBaseURI}/playlist/create`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify(playlistObject),
    });
    await this.checkStatus(response);
    const result = await response.json();

    return result.playlist_mbid;
  };

  editPlaylist = async (
    userToken: string,
    playlistMBID: string,
    playlistObject: JSPFObject
  ): Promise<number> => {
    if (!playlistMBID) {
      throw new SyntaxError("Playlist MBID is missing");
    }

    const url = `${this.APIBaseURI}/playlist/edit/${playlistMBID}`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify(playlistObject),
    });
    await this.checkStatus(response);

    return response.status;
  };

  getUserPlaylists = async (
    userName: string,
    userToken?: string,
    offset: number = 0,
    count: number = 25,
    createdFor: boolean = false,
    collaborator: boolean = false
  ) => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    let headers;
    if (userToken) {
      headers = {
        Authorization: `Token ${userToken}`,
      };
    }

    const url = `${this.APIBaseURI}/user/${userName}/playlists${
      createdFor ? "/createdfor" : ""
    }${collaborator ? "/collaborator" : ""}?offset=${offset}&count=${count}`;

    const response = await fetch(url, {
      method: "GET",
      headers,
    });

    await this.checkStatus(response);
    const data = response.json();
    return data;
  };

  getPlaylist = async (playlistMBID: string, userToken?: string) => {
    if (!playlistMBID) {
      throw new SyntaxError("playlist MBID missing");
    }
    let headers;
    if (userToken) {
      headers = {
        Authorization: `Token ${userToken}`,
      };
    }

    const url = `${this.APIBaseURI}/playlist/${playlistMBID}`;
    const response = await fetch(url, {
      method: "GET",
      headers,
    });
    await this.checkStatus(response);
    const data = response.json();
    return data;
  };

  addPlaylistItems = async (
    userToken: string,
    playlistMBID: string,
    tracks: JSPFTrack[],
    offset?: number
  ): Promise<number> => {
    if (!playlistMBID) {
      throw new SyntaxError("Playlist MBID is missing");
    }
    const optionalOffset =
      !isNil(offset) && Number.isSafeInteger(offset) ? `?offset=${offset}` : "";
    const url = `${this.APIBaseURI}/playlist/${playlistMBID}/item/add${optionalOffset}`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ playlist: { track: tracks } }),
    });
    await this.checkStatus(response);

    return response.status;
  };

  deletePlaylistItems = async (
    userToken: string,
    playlistMBID: string,
    // This is currently unused by the API endpoint, which might be an oversight
    recordingMBID: string,
    index: number,
    count: number = 1
  ): Promise<number> => {
    if (!playlistMBID) {
      throw new SyntaxError("Playlist MBID is missing");
    }
    const url = `${this.APIBaseURI}/playlist/${playlistMBID}/item/delete`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ index, count }),
    });
    await this.checkStatus(response);

    return response.status;
  };

  movePlaylistItem = async (
    userToken: string,
    playlistMBID: string,
    recordingMBID: string,
    from: number,
    to: number,
    count: number
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/playlist/${playlistMBID}/item/move`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ mbid: recordingMBID, from, to, count }),
    });
    await this.checkStatus(response);

    return response.status;
  };

  copyPlaylist = async (
    userToken: string,
    playlistMBID: string
  ): Promise<string> => {
    if (!playlistMBID) {
      throw new SyntaxError("playlist MBID missing");
    }

    const url = `${this.APIBaseURI}/playlist/${playlistMBID}/copy`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
      },
    });
    await this.checkStatus(response);
    const data = await response.json();
    return data.playlist_mbid;
  };

  deletePlaylist = async (
    userToken: string,
    playlistMBID: string
  ): Promise<number> => {
    if (!playlistMBID) {
      throw new SyntaxError("playlist MBID missing");
    }

    const url = `${this.APIBaseURI}/playlist/${playlistMBID}/delete`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
      },
    });
    await this.checkStatus(response);
    return response.status;
  };

  submitRecommendationFeedback = async (
    userToken: string,
    recordingMBID: string,
    rating: RecommendationFeedBack
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/recommendation/feedback/submit`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ recording_mbid: recordingMBID, rating }),
    });
    this.checkStatus(response);
    return response.status;
  };

  deleteRecommendationFeedback = async (
    userToken: string,
    recordingMBID: string
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/recommendation/feedback/delete`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ recording_mbid: recordingMBID }),
    });
    this.checkStatus(response);
    return response.status;
  };

  getFeedbackForUserForRecommendations = async (
    userName: string,
    recordings: string
  ) => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }

    const url = `${this.APIBaseURI}/recommendation/feedback/user/${userName}/recordings?mbids=${recordings}`;
    const response = await fetch(url);
    this.checkStatus(response);
    const data = response.json();
    return data;
  };
}
