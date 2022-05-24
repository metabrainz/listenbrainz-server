import { isNil, isUndefined, omit } from "lodash";
import APIError from "./APIError";

export default class APIService {
  APIBaseURI: string;

  MBBaseURI: string = "https://musicbrainz.org/ws/2";
  CBBaseURI: string = "https://critiquebrainz.org/ws/1";

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
    await this.checkStatus(response);
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
    await this.checkStatus(response);
    const result = await response.json();

    return result.payload.listens;
  };

  getFeedForUser = async (
    userName: string,
    userToken: string,
    minTs?: number,
    maxTs?: number,
    count?: number
  ): Promise<Array<TimelineEvent>> => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    if (!userToken) {
      throw new SyntaxError("User token missing");
    }

    let query: string = `${this.APIBaseURI}/user/${userName}/feed/events`;

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
      headers: {
        Authorization: `Token ${userToken}`,
      },
    });
    await this.checkStatus(response);
    const result = await response.json();

    return result.payload.events;
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

  refreshYoutubeToken = async (): Promise<string> => {
    return this.refreshAccessToken("youtube");
  };

  refreshSpotifyToken = async (): Promise<string> => {
    return this.refreshAccessToken("spotify");
  };

  refreshCritiquebrainzToken = async (): Promise<string> => {
    return this.refreshAccessToken("critiquebrainz");
  };

  refreshAccessToken = async (service: string): Promise<string> => {
    const response = await fetch(
      `/profile/music-services/${service}/refresh/`,
      {
        method: "POST",
      }
    );
    await this.checkStatus(response);
    const result = await response.json();
    return result.access_token;
  };

  followUser = async (
    userName: string,
    userToken: string
  ): Promise<{ status: number }> => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    if (!userToken) {
      throw new SyntaxError("User token missing");
    }
    const response = await fetch(`${this.APIBaseURI}/user/${userName}/follow`, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
      },
    });
    return { status: response.status };
  };

  unfollowUser = async (
    userName: string,
    userToken: string
  ): Promise<{ status: number }> => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    if (!userToken) {
      throw new SyntaxError("User token missing");
    }
    const response = await fetch(
      `${this.APIBaseURI}/user/${userName}/unfollow`,
      {
        method: "POST",
        headers: {
          Authorization: `Token ${userToken}`,
        },
      }
    );
    return { status: response.status };
  };

  getFollowersOfUser = async (
    username: string
  ): Promise<{ followers: Array<string> }> => {
    if (!username) {
      throw new SyntaxError("Username missing");
    }

    const url = `${this.APIBaseURI}/user/${username}/followers`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  getFollowingForUser = async (
    username: string
  ): Promise<{ following: Array<string> }> => {
    if (!username) {
      throw new SyntaxError("Username missing");
    }

    const url = `${this.APIBaseURI}/user/${username}/following`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  getPlayingNowForUser = async (
    username: string
  ): Promise<Listen | undefined> => {
    if (!username) {
      throw new SyntaxError("Username missing");
    }

    const url = `${this.APIBaseURI}/user/${username}/playing-now`;
    const response = await fetch(url);
    await this.checkStatus(response);
    const result = await response.json();
    return result.payload.listens?.[0];
  };

  /*
     Send a POST request to the ListenBrainz server to submit a listen
   */
  submitListens = async (
    userToken: string,
    listenType: ListenType,
    payload: Array<Listen>,
    retries: number = 3
  ): Promise<Response> => {
    let processedPayload = payload;
    // When submitting playing_now listens, listened_at must NOT be present
    if (listenType === "playing_now") {
      processedPayload = payload.map(
        (listen) => omit(listen, "listened_at") as Listen
      );
    }
    if (JSON.stringify(processedPayload).length <= this.MAX_LISTEN_SIZE) {
      // Payload is within submission limit, submit directly
      const struct = {
        listen_type: listenType,
        payload: processedPayload,
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
        if (response.status !== 429) {
          return response; // Return response so that caller can handle appropriately
        }
        if (!response.ok) {
          if (retries > 0) {
            // Rate limit error, this should never happen, but if it does, try again in 3 seconds.
            await new Promise((resolve) => {
              setTimeout(resolve, 3000);
            });
            return this.submitListens(
              userToken,
              listenType,
              payload,
              retries - 1
            );
          }
          return response;
        }
      } catch (error) {
        if (retries > 0) {
          // Retry if there is an network error
          await new Promise((resolve) => {
            setTimeout(resolve, 3000);
          });
          return this.submitListens(
            userToken,
            listenType,
            payload,
            retries - 1
          );
        }

        throw error;
      }
    }

    // Payload is not within submission limit, split and submit
    const payload1 = payload.slice(0, payload.length / 2);
    const payload2 = payload.slice(payload.length / 2, payload.length);
    return this.submitListens(userToken, listenType, payload1, retries)
      .then((response1) =>
        // Succes of first request, now do the second one
        this.submitListens(userToken, listenType, payload2, retries)
      )
      .then((response2) => response2)
      .catch((error) => {
        if (retries > 0) {
          return this.submitListens(
            userToken,
            listenType,
            payload,
            retries - 1
          );
        }
        return error;
      });
  };

  /*
   *  Send a GET request to the ListenBrainz server to get the latest import time
   *  from previous imports for the user.
   */
  getLatestImport = async (
    userName: string,
    service: ImportService
  ): Promise<number> => {
    const url = encodeURI(
      `${this.APIBaseURI}/latest-import?user_name=${userName}&service=${service}`
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
    service: ImportService,
    timestamp: number
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/latest-import`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ ts: timestamp, service }),
    });
    await this.checkStatus(response);
    return response.status; // Return true if timestamp is updated
  };

  getUserEntity = async (
    userName: string | undefined,
    entity: Entity,
    range: UserStatsAPIRange = "all_time",
    offset: number = 0,
    count?: number
  ): Promise<UserEntityResponse> => {
    let url;
    if (userName) {
      url = `${this.APIBaseURI}/stats/user/${userName}/`;
    } else {
      url = `${this.APIBaseURI}/stats/sitewide/`;
    }
    url += `${entity}s?offset=${offset}&range=${range}`;
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
    return response.json();
  };

  getUserListeningActivity = async (
    userName?: string,
    range: UserStatsAPIRange = "all_time"
  ): Promise<UserListeningActivityResponse> => {
    let url;
    if (userName) {
      url = `${this.APIBaseURI}/stats/user/${userName}/listening-activity`;
    } else {
      url = `${this.APIBaseURI}/stats/sitewide/listening-activity`;
    }
    const response = await fetch(`${url}?range=${range}`);
    await this.checkStatus(response);
    if (response.status === 204) {
      const error = new APIError(`HTTP Error ${response.statusText}`);
      error.status = response.statusText;
      error.response = response;
      throw error;
    }
    return response.json();
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
    return response.json();
  };

  getUserArtistMap = async (
    userName?: string,
    range: UserStatsAPIRange = "all_time",
    forceRecalculate: boolean = false
  ) => {
    let url;
    if (userName) {
      url = `${this.APIBaseURI}/stats/user/${userName}/`;
    } else {
      url = `${this.APIBaseURI}/stats/sitewide/`;
    }
    url += `artist-map?range=${range}&force_recalculate=${forceRecalculate}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    if (response.status === 204) {
      const error = new APIError(`HTTP Error ${response.statusText}`);
      error.status = response.statusText;
      error.response = response;
      throw error;
    }
    return response.json();
  };

  checkStatus = async (response: Response): Promise<void> => {
    if (response.status >= 200 && response.status < 300) {
      return;
    }
    let message = `HTTP Error ${response.statusText}`;
    try {
      const contentType = response.headers?.get("content-type");
      if (contentType && contentType.indexOf("application/json") !== -1) {
        const jsonError = await response.json();
        message = jsonError.error;
      } else if (typeof response.text === "function") {
        message = await response.text();
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.log("Error in parsing response in APIService checkStatus:", err);
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
    score: ListenFeedBack,
    recordingMSID?: string,
    recordingMBID?: string
  ): Promise<number> => {
    const url = `${this.APIBaseURI}/feedback/recording-feedback`;
    const body: any = { score };
    if (recordingMSID) {
      body.recording_msid = recordingMSID;
    }
    if (recordingMBID) {
      body.recording_mbid = recordingMBID;
    }
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify(body),
    });
    await this.checkStatus(response);
    return response.status;
  };

  getFeedbackForUser = async (
    userName: string,
    offset: number = 0,
    count?: number,
    score?: ListenFeedBack
  ) => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    let queryURL = `${this.APIBaseURI}/feedback/user/${userName}/get-feedback`;
    const queryParams: Array<string> = ["metadata=true"];
    if (!isUndefined(offset)) {
      queryParams.push(`offset=${offset}`);
    }
    if (!isUndefined(score)) {
      queryParams.push(`score=${score}`);
    }
    if (!isUndefined(count)) {
      queryParams.push(`count=${count}`);
    }
    if (queryParams.length) {
      queryURL += `?${queryParams.join("&")}`;
    }
    const response = await fetch(queryURL);
    await this.checkStatus(response);
    return response.json();
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
    return response.json();
  };

  getFeedbackForUserForRecordingsNew = async (
    userName: string,
    recording_msids: string,
    recording_mbids: string
  ) => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }

    const url = `${this.APIBaseURI}/feedback/user/${userName}/get-feedback-for-recordings?recording_msids=${recording_msids}&recording_mbids=${recording_mbids}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  getFeedbackForUserForMBIDs = async (
    userName: string,
    recording_mbids: string // Comma-separated list of MBIDs
  ) => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    const url = `${this.APIBaseURI}/feedback/user/${userName}/get-feedback-for-recordings?recording_mbids=${recording_mbids}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
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
    return response.json();
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
    return response.json();
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
    await this.checkStatus(response);
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
    await this.checkStatus(response);
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
    await this.checkStatus(response);
    return response.json();
  };

  recommendTrackToFollowers = async (
    userName: string,
    authToken: string,
    metadata: UserTrackRecommendationMetadata
  ) => {
    const url = `${this.APIBaseURI}/user/${userName}/timeline-event/create/recording`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${authToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ metadata }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  getSimilarUsersForUser = async (
    username: string
  ): Promise<{
    payload: Array<{ user_name: string; similarity: number }>;
  }> => {
    if (!username) {
      throw new SyntaxError("Username missing");
    }

    const url = `${this.APIBaseURI}/user/${username}/similar-users`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  reportUser = async (userName: string, optionalContext?: string) => {
    const response = await fetch(`/user/${userName}/report-user/`, {
      method: "POST",
      body: JSON.stringify({ reason: optionalContext }),
      headers: {
        "Content-Type": "application/json",
      },
    });
    await this.checkStatus(response);
  };

  submitPinRecording = async (
    userToken: string,
    recordingMSID: string,
    recordingMBID?: string,
    blurb_content?: string
  ): Promise<{ status: string; data: PinnedRecording }> => {
    const url = `${this.APIBaseURI}/pin`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({
        recording_msid: recordingMSID,
        recording_mbid: recordingMBID,
        blurb_content,
      }),
    });
    await this.checkStatus(response);
    return response.json();
  };

  unpinRecording = async (userToken: string): Promise<number> => {
    const url = `${this.APIBaseURI}/pin/unpin`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.status;
  };

  deletePin = async (userToken: string, pinID: number): Promise<number> => {
    const url = `${this.APIBaseURI}/pin/delete/${pinID}`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.status;
  };

  getPinsForUser = async (userName: string, offset: number, count: number) => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }

    const query = `${this.APIBaseURI}/${userName}/pins?offset=${offset}&count=${count}`;

    const response = await fetch(query, {
      method: "GET",
    });

    await this.checkStatus(response);
    return response.json();
  };

  submitReviewToCB = async (
    userName: string,
    userToken: string,
    review: CritiqueBrainzReview
  ) => {
    const url = `${this.APIBaseURI}/user/${userName}/timeline-event/create/review`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({
        metadata: {
          entity_name: review.entity_name,
          entity_id: review.entity_id,
          entity_type: review.entity_type,
          text: review.text,
          language: review.languageCode,
          rating: review.rating,
        },
      }),
    });

    await this.checkStatus(response);
    return response.json();
  };

  lookupMBRelease = async (releaseMBID: string): Promise<any> => {
    const url = `${this.MBBaseURI}/release/${releaseMBID}?fmt=json&inc=release-groups`;
    const response = await fetch(encodeURI(url));
    await this.checkStatus(response);
    return response.json();
  };

  lookupMBReleaseFromTrack = async (trackMBID: string): Promise<any> => {
    const url = `${this.MBBaseURI}/release?track=${trackMBID}&fmt=json`;
    const response = await fetch(encodeURI(url));
    await this.checkStatus(response);
    return response.json();
  };

  lookupReleaseFromColor = async (
    color: string,
    count?: number
  ): Promise<any> => {
    let query = `${this.APIBaseURI}/color/${color}`;
    if (!isUndefined(count)) query += `?count=${count}`;
    const response = await fetch(query);
    await this.checkStatus(response);
    return response.json();
  };

  deleteFeedEvent = async (
    eventType: string,
    username: string,
    userToken: string,
    id: number
  ): Promise<any> => {
    if (!id) {
      throw new SyntaxError("Event ID not present");
    }
    const query = `${this.APIBaseURI}/user/${username}/feed/events/delete`;
    const response = await fetch(query, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ event_type: eventType, id }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  hideFeedEvent = async (
    eventType: string,
    username: string,
    userToken: string,
    event_id: number
  ): Promise<any> => {
    if (!event_id) {
      throw new SyntaxError("Event ID not present");
    }
    const query = `${this.APIBaseURI}/user/${username}/feed/events/hide`;
    const response = await fetch(query, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ event_type: eventType, event_id }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  unhideFeedEvent = async (
    eventType: string,
    username: string,
    userToken: string,
    event_id: number
  ): Promise<any> => {
    if (!event_id) {
      throw new SyntaxError("Event ID not present");
    }
    const query = `${this.APIBaseURI}/user/${username}/feed/events/unhide`;
    const response = await fetch(query, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ event_type: eventType, event_id }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  lookupRecordingMetadata = async (
    trackName: string,
    artistName: string
  ): Promise<MetadataLookup | null> => {
    if (!trackName) {
      return null;
    }
    const queryParams: any = {
      recording_name: trackName,
      metadata: true,
    };
    if (artistName) {
      queryParams.artist_name = artistName;
    }
    const url = new URL(`${this.APIBaseURI}/metadata/lookup/`);
    // Iterate and add each queryParams
    Object.keys(queryParams).map((key) =>
      url.searchParams.append(key, queryParams[key])
    );
    url.searchParams.append("inc", "artist tag release");

    const response = await fetch(url.toString());
    await this.checkStatus(response);
    return response.json();
  };
}
