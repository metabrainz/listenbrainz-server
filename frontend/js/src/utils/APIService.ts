import { isNil, isUndefined, kebabCase, lowerCase, omit } from "lodash";
import { TagActionType } from "../tags/TagComponent";
import type { SortOption } from "../explore/fresh-releases/FreshReleases";
import APIError from "./APIError";
import type { Flair } from "./constants";

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

  getListensFromFollowedUsers = async (
    userName: string,
    userToken: string,
    minTs?: number,
    maxTs?: number,
    count?: number
  ): Promise<Array<TimelineEvent<Listen>>> => {
    if (maxTs && minTs) {
      throw new SyntaxError(
        "Cannot have both minTs and maxTs defined at the same time"
      );
    }
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    if (!userToken) {
      throw new SyntaxError("User token missing");
    }

    let query: string = `${this.APIBaseURI}/user/${userName}/feed/events/listens/following`;

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

  getListensFromSimilarUsers = async (
    userName: string,
    userToken: string,
    minTs?: number,
    maxTs?: number,
    count?: number
  ): Promise<Array<TimelineEvent<Listen>>> => {
    if (maxTs && minTs) {
      throw new SyntaxError(
        "Cannot have both minTs and maxTs defined at the same time"
      );
    }
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    if (!userToken) {
      throw new SyntaxError("User token missing");
    }

    let query: string = `${this.APIBaseURI}/user/${userName}/feed/events/listens/similar`;

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

  getFeedForUser = async (
    userName: string,
    userToken: string,
    minTs?: number,
    maxTs?: number,
    count?: number
  ): Promise<Array<TimelineEvent<EventMetadata>>> => {
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

  refreshSoundcloudToken = async (): Promise<string> => {
    return this.refreshAccessToken("soundcloud");
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

  refreshMusicbrainzToken = async (): Promise<string> => {
    return this.refreshAccessToken("musicbrainz");
  };

  refreshAccessToken = async (service: string): Promise<string> => {
    const response = await fetch(
      `/settings/music-services/${service}/refresh/`,
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

  searchUsers = async (
    userName: string
  ): Promise<{ users: Array<SearchUser> }> => {
    try {
      const url = new URL(`${this.APIBaseURI}/search/users/`);
      url.searchParams.append("search_term", userName);
      const response = await fetch(url.toString(), {
        method: "GET",
      });

      await this.checkStatus(response);

      const parsedResponse = await response.json();
      return { users: parsedResponse.users };
    } catch (err) {
      // eslint-disable-next-line no-console
      console.log("Error in parsing response in APIService searchUsers:", err);
      throw err;
    }
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
      const error = new APIError(
        "There are no statistics available for this user for this period"
      );
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
      const error = new APIError(
        "There are no statistics available for this user for this period"
      );
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
      const error = new APIError(
        "There are no statistics available for this user for this period"
      );
      error.status = response.statusText;
      error.response = response;
      throw error;
    }
    return response.json();
  };

  getUserArtistActivity = async (
    userName?: string,
    range: UserStatsAPIRange = "all_time"
  ): Promise<UserArtistActivityResponse> => {
    let url;
    if (userName) {
      url = `${this.APIBaseURI}/stats/user/${userName}/artist-activity`;
    } else {
      url = `${this.APIBaseURI}/stats/sitewide/artist-activity`;
    }
    url += `?range=${range}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    if (response.status === 204) {
      const error = new APIError(
        "There are no statistics available for this user for this period"
      );
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
      const error = new APIError(
        "There are no statistics available for this user for this period"
      );
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

  /**
   * Import feedback data from thir party services
   * @param  {string} userToken
   * @param  {string} userName
   * @param  {ImportService} service
   */
  importFeedback = async (
    userToken: string,
    userName: string,
    service: ImportService
  ): Promise<{
    inserted: number;
    invalid_mbid: number;
    mbid_not_found: number;
    missing_mbid: number;
    total: number;
  }> => {
    const url = `${this.APIBaseURI}/feedback/import`;
    if (!userName || !userToken || !service) {
      throw new Error("Missing user name, token or external service name");
    }
    const body = {
      user_name: userName,
      service,
    };
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify(body),
    });
    await this.checkStatus(response);
    return response.json();
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
    recording_mbids: string[],
    recording_msids?: string[]
  ) => {
    if (!userName) {
      throw new SyntaxError("Username missing");
    }
    const url = `${this.APIBaseURI}/feedback/user/${userName}/get-feedback-for-recordings`;
    const requestBody: FeedbackForUserForRecordingsRequestBody = {
      recording_mbids,
    };
    if (recording_msids?.length) {
      requestBody.recording_msids = recording_msids;
    }
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify(requestBody),
    });
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
  ): Promise<{
    playlists: JSPFObject[];
    playlist_count: number;
    count: string;
    offset: string;
  }> => {
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
    return response;
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

  getSimilarityBetweenUsers = async (
    userName: string,
    otherUserName: string
  ): Promise<{
    payload: { user_name: string; similarity: number };
  }> => {
    if (!userName || !otherUserName) {
      throw new SyntaxError("One username missing");
    }

    const url = `${this.APIBaseURI}/user/${userName}/similar-to/${otherUserName}`;
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

  updatePinRecordingBlurbContent = async (
    userToken: string,
    rowId: number,
    blurbContent: string
  ): Promise<{ status: string }> => {
    const url = `${this.APIBaseURI}/pin/update/${rowId}`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({
        blurb_content: blurbContent,
      }),
    });
    await this.checkStatus(response);
    return response.json();
  };

  submitMBIDMapping = async (
    userToken: string,
    recordingMSID: string,
    recordingMBID: string
  ): Promise<{ status: string }> => {
    const url = `${this.APIBaseURI}/metadata/submit_manual_mapping/`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({
        recording_msid: recordingMSID,
        recording_mbid: recordingMBID,
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

  lookupMBArtist = async (
    artistMBID: string,
    inc?: string
  ): Promise<Array<MusicBrainzArtist>> => {
    let url = `${this.APIBaseURI}/metadata/artist/?artist_mbids=${artistMBID}`;
    if (inc) {
      url += `&inc=${inc}`;
    }
    const response = await fetch(encodeURI(url));
    await this.checkStatus(response);
    return response.json();
  };

  importPlaylistFromSpotify = async (userToken?: string): Promise<any> => {
    const url = `${this.APIBaseURI}/playlist/import/spotify`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.json();
  };

  importPlaylistFromAppleMusic = async (userToken?: string): Promise<any> => {
    const url = `${this.APIBaseURI}/playlist/import/apple_music`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.json();
  };

  importSpotifyPlaylistTracks = async (
    userToken: string,
    playlistID: string
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/playlist/spotify/${playlistID}/tracks`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.json();
  };

  importAppleMusicPlaylistTracks = async (
    userToken: string,
    playlistID: string
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/playlist/apple_music/${playlistID}/tracks`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.json();
  };

  lookupMBRecording = async (
    recordingMBID: string,
    inc = "artists"
  ): Promise<MusicBrainzRecording> => {
    const url = `${this.MBBaseURI}/recording/${recordingMBID}?fmt=json&inc=${inc}`;
    const response = await fetch(encodeURI(url));
    await this.checkStatus(response);
    return response.json();
  };

  lookupMBRelease = async (
    releaseMBID: string,
    inc = "release-groups"
  ): Promise<
    (MusicBrainzRelease & WithReleaseGroup) | (MusicBrainzRelease & WithMedia)
  > => {
    const url = `${this.MBBaseURI}/release/${releaseMBID}?fmt=json&inc=${inc}`;
    const response = await fetch(encodeURI(url));
    await this.checkStatus(response);
    return response.json();
  };

  lookupMBReleaseGroup = async (
    releaseGroupMBID: string
  ): Promise<
    MusicBrainzReleaseGroup &
      WithArtistCredits & {
        releases: Array<MusicBrainzRelease & WithMedia>;
      }
  > => {
    const url = `${this.MBBaseURI}/release-group/${releaseGroupMBID}?fmt=json&inc=releases+artists+media`;
    const response = await fetch(encodeURI(url));
    await this.checkStatus(response);
    return response.json();
  };

  lookupMBReleaseFromTrack = async (
    trackMBID: string
  ): Promise<{
    "release-offset": number;
    "release-count": number;
    releases: Array<MusicBrainzRelease & WithMedia>;
  }> => {
    const url = `${this.MBBaseURI}/release?track=${trackMBID}&fmt=json`;
    const response = await fetch(encodeURI(url));
    await this.checkStatus(response);
    return response.json();
  };

  lookupReleaseFromColor = async (
    color: string,
    count?: number
  ): Promise<any> => {
    let query = `${this.APIBaseURI}/explore/color/${color}`;
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

  thankFeedEvent = async (
    event_id: number | undefined,
    eventType: EventTypeT,
    userToken: string,
    username: string,
    blurb_content: string
  ): Promise<any> => {
    if (!event_id) {
      throw new SyntaxError("Event ID not present");
    }
    const query = `${this.APIBaseURI}/user/${username}/timeline-event/create/thanks`;
    const response = await fetch(query, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({
        metadata: {
          original_event_type: eventType,
          original_event_id: event_id,
          blurb_content,
        },
      }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  lookupRecordingMetadata = async (
    trackName: string,
    artistName: string,
    metadata: boolean = true
  ): Promise<MetadataLookup | null> => {
    if (!trackName) {
      return null;
    }
    const queryParams: any = {
      recording_name: trackName,
    };
    if (artistName) {
      queryParams.artist_name = artistName;
    }
    if (metadata) {
      queryParams.metadata = true;
    }
    const url = new URL(`${this.APIBaseURI}/metadata/lookup/`);
    // Iterate and add each queryParams
    Object.keys(queryParams).map((key) =>
      url.searchParams.append(key, queryParams[key])
    );
    if (metadata) {
      url.searchParams.append("inc", "artist tag release");
    }

    const response = await fetch(url.toString());
    await this.checkStatus(response);
    return response.json();
  };

  getRecordingMetadata = async (
    recordingMBIDs: string[],
    metadata: boolean = true
  ): Promise<{ [mbid: string]: ListenMetadata } | null> => {
    if (!recordingMBIDs?.length) {
      return null;
    }
    const url = new URL(`${this.APIBaseURI}/metadata/recording/`);

    url.searchParams.append("recording_mbids", recordingMBIDs.join(","));

    if (metadata) {
      url.searchParams.append("inc", "artist tag release");
    }

    const response = await fetch(url.toString());
    await this.checkStatus(response);
    return response.json();
  };

  resetUserTimezone = async (
    userToken: string,
    zonename: string
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/settings/timezone`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ zonename }),
    });

    await this.checkStatus(response);
    return response.status;
  };

  submitPersonalRecommendation = async (
    userToken: string,
    userName: string,
    metadata: UserTrackPersonalRecommendationMetadata
  ) => {
    const url = `${this.APIBaseURI}/user/${userName}/timeline-event/create/recommend-personal`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ metadata }),
    });

    await this.checkStatus(response);
    return response.status;
  };

  submitTroiPreferences = async (
    userToken: string,
    exportToSpotify: boolean
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/settings/troi`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ export_to_spotify: exportToSpotify }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  submitBrainzplayerPreferences = async (
    userToken: string,
    brainzPlayerSettings: BrainzPlayerSettings
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/settings/brainzplayer`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify(brainzPlayerSettings),
    });
    await this.checkStatus(response);
    return response.status;
  };

  submitFlairPreferences = async (
    userToken: string,
    flair: Flair
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/settings/flair`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ flair }),
    });
    await this.checkStatus(response);
    return response.status;
  };

  exportPlaylistToSpotify = async (
    userToken: string,
    playlist_mbid: string
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/playlist/${playlist_mbid}/export/spotify`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.json();
  };

  exportPlaylistToAppleMusic = async (
    userToken: string,
    playlist_mbid: string
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/playlist/${playlist_mbid}/export/apple_music`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.json();
  };

  exportJSPFPlaylistToAppleMusic = async (
    userToken: string,
    playlist: JSPFPlaylist
  ): Promise<any> => {
    const url = `${this.APIBaseURI}/playlist/export-jspf/apple_music`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify(playlist),
    });
    await this.checkStatus(response);
    return response.json();
  };

  exportJSPFPlaylistToSpotify = async (
    userToken: string,
    playlist: JSPFPlaylist
  ): Promise<any> => {
    if (!playlist) {
      throw new Error("Expected a playlist");
    }
    const url = `${this.APIBaseURI}/playlist/export-jspf/spotify`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify(playlist),
    });
    await this.checkStatus(response);
    return response.json();
  };

  exportPlaylistToXSPF = async (
    userToken: string,
    playlist_mbid: string
  ): Promise<Blob> => {
    const url = `${this.APIBaseURI}/playlist/${playlist_mbid}/xspf`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/xspf+xml;charset=UTF-8",
      },
    });
    await this.checkStatus(response);
    return response.blob();
  };

  fetchSitewideFreshReleases = async (
    days?: number,
    past?: boolean,
    future?: boolean,
    sort?: SortOption,
    release_date?: string
  ): Promise<any> => {
    let url = `${this.APIBaseURI}/explore/fresh-releases/`;

    const queryParams: Array<string> = [];
    if (days) {
      queryParams.push(`days=${days}`);
    }
    if (past === false) {
      queryParams.push(`past=${past}`);
    }
    if (future === false) {
      queryParams.push(`future=${future}`);
    }
    if (sort) {
      queryParams.push(`sort=${sort}`);
    }
    if (release_date) {
      queryParams.push(`release_date=${release_date}`);
    }
    if (queryParams.length) {
      url += `?${queryParams.join("&")}`;
    }

    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  fetchUserFreshReleases = async (
    username: string,
    past?: boolean,
    future?: boolean,
    sort?: SortOption
  ): Promise<any> => {
    if (!username) {
      throw new SyntaxError("Username missing");
    }
    let url = `${this.APIBaseURI}/user/${username}/fresh_releases`;

    const queryParams: Array<string> = [];
    if (sort) {
      queryParams.push(`sort=${sort}`);
    }

    if (past === false) {
      queryParams.push(`past=${past}`);
    }

    if (future === false) {
      queryParams.push(`future=${future}`);
    }
    if (queryParams.length) {
      url += `?${queryParams.join("&")}`;
    }
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };
  /** MusicBrainz */

  submitTagToMusicBrainz = async (
    entityType: string,
    entityMBID: string,
    tagName: string,
    action: TagActionType,
    musicBrainzAuthToken: string,
    retries: number = 2
  ): Promise<boolean> => {
    const formattedEntityName = kebabCase(entityType);
    // encode reserved characters
    const safeTagName = tagName
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
    try {
      const parser = new DOMParser();
      const xmlDocument = parser.parseFromString(
        `
        <metadata xmlns="http://musicbrainz.org/ns/mmd-2.0#">
          <${formattedEntityName}-list>
              <${formattedEntityName} id="${entityMBID}">
                  <user-tag-list>
                      <user-tag vote="${lowerCase(
                        action
                      )}"><name>${safeTagName}</name></user-tag>
                  </user-tag-list>
              </${formattedEntityName}>
          </${formattedEntityName}-list>
        </metadata>
      `,
        "application/xml"
      );

      // Check if the XML parsing threw an error; if so the first element will be a <parseerror>
      const isInvalid =
        xmlDocument.documentElement?.childNodes?.[0]?.nodeName ===
        "parsererror";
      if (isInvalid) {
        // Get the error text content from the <parseerror> element
        const errorText =
          xmlDocument.documentElement.childNodes[0].childNodes?.[1]
            ?.textContent;
        throw SyntaxError(`Invalid XML: ${errorText}`);
      }

      const url = `${this.MBBaseURI}/tag?client=listenbrainz-listening-now`;
      const serializer = new XMLSerializer();
      const body = serializer.serializeToString(xmlDocument);
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/xml; charset=utf-8",
          Authorization: `Bearer ${musicBrainzAuthToken}`,
        },
        body,
      });
      if (response.ok) {
        return true;
      }
      if (retries > 0) {
        let token = musicBrainzAuthToken;
        if (response.status === 401) {
          // Token is probably expired, refresh it before trying again
          // Currently the error messgae and status is the same for wrong credentials
          // and expired token, so we can't know exactly what the issue is. See MBS-13068
          token = await this.refreshMusicbrainzToken();
        }
        return this.submitTagToMusicBrainz(
          entityType,
          entityMBID,
          tagName,
          action,
          token,
          retries - 1
        );
      }
      return false;
    } catch (err) {
      console.error(err);
      return false;
    }
  };

  artistLookup = async (
    searchQuery: string,
    offset: number = 0,
    count: number = 25
  ): Promise<ArtistTypeSearchResult> => {
    const url = `${this.MBBaseURI}/artist?query=${searchQuery}&fmt=json&offset=${offset}&limit=${count}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  albumLookup = async (
    searchQuery: string,
    offset: number = 0,
    count: number = 25
  ): Promise<AlbumTypeSearchResult> => {
    const url = `${this.MBBaseURI}/release-group?query=${searchQuery}&fmt=json&offset=${offset}&limit=${count}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  recordingLookup = async (
    searchQuery: string,
    offset: number = 0,
    count: number = 25
  ): Promise<TrackTypeSearchResult> => {
    const url = `${this.MBBaseURI}/recording?query=${searchQuery}&fmt=json&offset=${offset}&limit=${count}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  searchMBRelease = async (
    searchQuery: string
  ): Promise<{
    count: number;
    offset: number;
    releases: Array<
      MusicBrainzRelease & WithReleaseGroup & WithArtistCredits & WithMedia
    >;
  }> => {
    const url = `${this.MBBaseURI}/release?query=${searchQuery}&fmt=json`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  getArtistWikipediaExtract = async (artistMBID: string): Promise<string> => {
    const url = `https://musicbrainz.org/artist/${artistMBID}/wikipedia-extract`;
    const response = await fetch(url);
    const { wikipediaExtract } = await response.json();

    if (!wikipediaExtract || !wikipediaExtract.content) {
      return "No wiki data found.";
    }

    const htmlParser = new DOMParser();
    const htmlData = htmlParser.parseFromString(
      wikipediaExtract.content,
      "text/html"
    );
    const htmlParagraphs = htmlData.querySelector("p:not(.mw-empty-elt)");

    return htmlParagraphs?.textContent || "No wiki data found.";
  };

  getTopRecordingsForArtist = async (
    artistMBID: string
  ): Promise<RecordingType[]> => {
    const url = `${this.APIBaseURI}/popularity/top-recordings-for-artist/${artistMBID}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  getTopReleaseGroupsForArtist = async (
    artistMBID: string
  ): Promise<ReleaseGroupType[]> => {
    const url = `${this.APIBaseURI}/popularity/top-release-groups-for-artist/${artistMBID}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  searchPlaylistsForUser = async (
    searchQuery: string,
    musicbrainzID: string,
    count: number = 25,
    offset: number = 0
  ): Promise<PlaylistTypeSearchResult> => {
    const url = `${this.APIBaseURI}/user/${musicbrainzID}/playlists/search?query=${searchQuery}&count=${count}&offset=${offset}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  searchPlaylists = async (
    searchQuery: string,
    count: number = 25,
    offset: number = 0
  ): Promise<PlaylistTypeSearchResult> => {
    const url = `${this.APIBaseURI}/playlist/search?query=${searchQuery}&count=${count}&offset=${offset}`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };

  getUserFlairs = async (): Promise<Record<string, Flair>> => {
    const url = `${this.APIBaseURI}/donors/all-flairs`;
    const response = await fetch(url);
    await this.checkStatus(response);
    return response.json();
  };
}
