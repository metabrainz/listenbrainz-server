import * as React from "react";
import * as _ from "lodash";
import { isFinite, isUndefined } from "lodash";
import * as timeago from "time-ago";
import { Rating } from "react-simple-star-rating";
import { toast } from "react-toastify";
import ReactMarkdown from "react-markdown";
import SpotifyPlayer from "../common/brainzplayer/SpotifyPlayer";
import YoutubePlayer from "../common/brainzplayer/YoutubePlayer";
import SpotifyAPIService from "./SpotifyAPIService";
import NamePill from "../personal-recommendations/NamePill";
import { GlobalAppContextT } from "./GlobalAppContext";
import APIServiceClass from "./APIService";
import { ToastMsg } from "../notifications/Notifications";
import RecordingFeedbackManager from "./RecordingFeedbackManager";

const originalFetch = window.fetch;
const fetchWithRetry = require("fetch-retry")(originalFetch);

const searchForSpotifyTrack = async (
  spotifyToken?: string,
  trackName?: string,
  artistName?: string,
  releaseName?: string
): Promise<SpotifyTrack | null> => {
  if (!spotifyToken) {
    // eslint-disable-next-line no-throw-literal
    throw {
      status: 403,
      message: "You need to connect to your Spotify account",
    };
  }
  let queryString = `type=track&q=`;
  if (trackName) {
    queryString += `track:${encodeURIComponent(trackName)}`;
  }
  if (artistName) {
    queryString += ` artist:${encodeURIComponent(artistName)}`;
  }
  if (releaseName) {
    queryString += ` album:${encodeURIComponent(releaseName)}`;
  }

  const response = await fetch(
    `https://api.spotify.com/v1/search?${queryString}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${spotifyToken}`,
      },
    }
  );
  const responseBody = await response.json();
  if (!response.ok) {
    throw responseBody.error;
  }
  // Valid response
  const tracks: SpotifyTrack[] = _.get(responseBody, "tracks.items");
  if (tracks && tracks.length) {
    return tracks[0];
  }
  return null;
};

const searchForYoutubeTrack = async (
  apiKey?: string,
  trackName?: string,
  artistName?: string,
  releaseName?: string,
  refreshToken?: () => Promise<string>,
  onAccountError?: () => void
): Promise<Array<string> | null> => {
  if (!apiKey) return null;
  let query = trackName ?? "";
  if (artistName) {
    query += ` ${artistName}`;
  }
  // Considering we cannot tell the Youtube API that this should match only an album title,
  // results are paradoxically sometimes worse if we add it to the query (YT will find random matches for album title words)
  if (releaseName) {
    query += ` ${releaseName}`;
  }
  if (!query) {
    return null;
  }
  const response = await fetch(
    `https://youtube.googleapis.com/youtube/v3/search?part=snippet&q=${encodeURIComponent(
      query
    )}&videoEmbeddable=true&type=video&key=${apiKey}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (response.status === 401) {
    if (refreshToken) {
      try {
        return searchForYoutubeTrack(
          apiKey,
          trackName,
          artistName,
          releaseName,
          undefined
        );
      } catch (error) {
        // Run onAccountError if we can't refresh the token
        if (_.isFunction(onAccountError)) {
          onAccountError();
        }
      }
    }
    // Run onAccountError if we already tried refreshing the token but still getting 401
    if (_.isFunction(onAccountError)) {
      onAccountError();
    }
  }

  if (response.status === 429) {
    throw new Error(
      "We couldn't play this track because we ran out of Youtube quota, sorry about the inconvenience."
    );
  }

  const responseBody = await response.json();
  if (!response.ok) {
    throw responseBody.error;
  }
  const tracks: Array<any> = _.get(responseBody, "items");
  const videoIds = tracks.map((track) => track.id.videoId);
  if (videoIds.length) return videoIds;
  return null;
};

const searchForSoundcloudTrack = async (
  soundcloudToken: string,
  trackName?: string,
  artistName?: string,
  releaseName?: string
): Promise<string | null> => {
  let query = trackName ?? "";
  if (artistName) {
    query += ` ${artistName}`;
  }
  // Considering we cannot tell the Soundcloud API that this should match only an album title,
  // results are paradoxically sometimes worse if we add it to the query
  if (releaseName) {
    query += ` ${releaseName}`;
  }
  if (!query) {
    return null;
  }

  const response = await fetch(
    `https://api.soundcloud.com/tracks?q=${encodeURIComponent(
      query
    )}&access=playable`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `OAuth ${soundcloudToken}`,
      },
    }
  );
  const responseBody = await response.json();
  if (!response.ok) {
    throw responseBody;
  }
  return responseBody?.[0]?.uri ?? null;
};

const getAdditionalContent = (metadata: EventMetadata): string =>
  _.get(metadata, "blurb_content") ?? _.get(metadata, "text") ?? "";

const getArtistMBIDs = (listen: Listen): string[] | undefined => {
  const additionalInfoArtistMBIDs = _.get(
    listen,
    "track_metadata.additional_info.artist_mbids"
  );
  const mbidMappingArtistMBIDs = _.get(
    listen,
    "track_metadata.mbid_mapping.artist_mbids"
  );
  if (additionalInfoArtistMBIDs || mbidMappingArtistMBIDs) {
    return additionalInfoArtistMBIDs ?? mbidMappingArtistMBIDs;
  }

  // Backup: cast artist_mbid as an array if it exists
  const additionalInfoArtistMBID = _.get(
    listen,
    "track_metadata.additional_info.artist_mbid"
  );
  if (additionalInfoArtistMBID) {
    return [additionalInfoArtistMBID];
  }
  return undefined;
};

const getRecordingMSID = (listen: Listen): string =>
  _.get(listen, "track_metadata.additional_info.recording_msid");

const getRecordingMBID = (listen: Listen): string | undefined =>
  _.get(listen, "track_metadata.additional_info.recording_mbid") ??
  _.get(listen, "track_metadata.mbid_mapping.recording_mbid");

const getReleaseMBID = (listen: Listen): string | undefined =>
  _.get(listen, "track_metadata.additional_info.release_mbid") ??
  _.get(listen, "track_metadata.mbid_mapping.release_mbid");

const getReleaseGroupMBID = (listen: Listen): string | undefined =>
  _.get(listen, "track_metadata.additional_info.release_group_mbid") ??
  _.get(listen, "track_metadata.mbid_mapping.release_group_mbid");

const getReleaseName = (listen: Listen): string =>
  _.get(listen, "track_metadata.mbid_mapping.release_name", "") ||
  _.get(listen, "track_metadata.release_name", "");

const getTrackName = (listen?: Listen | JSPFTrack | PinnedRecording): string =>
  _.get(listen, "track_metadata.mbid_mapping.recording_name", "") ||
  _.get(listen, "track_metadata.track_name", "") ||
  _.get(listen, "title", "");

const getTrackDurationInMs = (listen?: Listen | JSPFTrack): number =>
  _.get(listen, "track_metadata.additional_info.duration_ms", "") ||
  _.get(listen, "track_metadata.additional_info.duration", "") * 1000 ||
  _.get(listen, "duration", "");

const getArtistName = (
  listen?: Listen | JSPFTrack | PinnedRecording
): string => {
  const artists: MBIDMappingArtist[] = _.get(
    listen,
    "track_metadata.mbid_mapping.artists",
    []
  );
  if (artists?.length) {
    return artists
      .map((artist) => `${artist.artist_credit_name}${artist.join_phrase}`)
      .join("");
  }
  return (
    _.get(listen, "track_metadata.artist_name", "") ||
    _.get(listen, "creator", "")
  );
};

const getMBIDMappingArtistLink = (artists: MBIDMappingArtist[]) => {
  return (
    <>
      {artists.map((artist) => (
        <>
          <a
            href={`/artist/${artist.artist_mbid}`}
            target="_blank"
            rel="noopener noreferrer"
            title={artist.artist_credit_name}
          >
            {artist.artist_credit_name}
          </a>
          {artist.join_phrase}
        </>
      ))}
    </>
  );
};

const getStatsArtistLink = (
  artists?: MBIDMappingArtist[],
  artist_name?: string,
  artist_mbids?: string[]
) => {
  if (artists?.length) {
    return getMBIDMappingArtistLink(artists);
  }
  const firstArtist = _.first(artist_mbids);
  if (firstArtist) {
    return (
      <a
        href={`/artist/${firstArtist}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {artist_name}
      </a>
    );
  }
  return artist_name;
};

const getArtistLink = (listen: Listen) => {
  const artists = listen.track_metadata?.mbid_mapping?.artists;
  const artist_name = getArtistName(listen);
  const artist_mbids = getArtistMBIDs(listen);
  return getStatsArtistLink(artists, artist_name, artist_mbids);
};

const getTrackLink = (listen: Listen): JSX.Element | string => {
  const trackName = getTrackName(listen);
  const recordingMbid = getRecordingMBID(listen);

  if (recordingMbid) {
    return (
      <a
        href={`https://musicbrainz.org/recording/${recordingMbid}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {trackName}
      </a>
    );
  }
  return trackName;
};

const getListenCardKey = (listen: Listen): string =>
  `${listen.listened_at}-${listen.user_name}-${getRecordingMSID(
    listen
  )}-${getTrackName(listen)}-${getArtistName(listen)}-${getReleaseName(
    listen
  )}-${
    listen.track_metadata?.mbid_mapping?.release_group_name
  }-${getRecordingMBID(listen)}-${getArtistMBIDs(listen)?.join(
    ","
  )}-${getReleaseMBID(listen)}-${getReleaseGroupMBID(listen)}-${
    listen.track_metadata?.mbid_mapping?.caa_id
  }-${listen.track_metadata?.mbid_mapping?.caa_release_mbid}`;

const formatWSMessageToListen = (wsMsg: any): Listen | null => {
  const json = wsMsg;
  try {
    // The websocket message received may not contain the expected track_metadata and listened_at fields.
    // Therefore, we look for their alias as well.
    if (!("track_metadata" in json)) {
      if ("data" in json) {
        json.track_metadata = json.data;
        delete json.data;
      } else {
        // eslint-disable-next-line no-console
        console.debug(
          "Could not find track_metadata and data in following json: ",
          json
        );
        return null;
      }
    }
    if (!("listened_at" in json)) {
      if ("timestamp" in json) {
        json.listened_at = json.timestamp;
        delete json.timestamp;
      } else {
        // eslint-disable-next-line no-console
        console.debug(
          "Could not find listened_at and timestamp in following json: ",
          json
        );
        return null;
      }
    }
    // The websocket message received contains the recording_msid as a top level key.
    // Therefore, we need to shift it json.track_metadata.additional_info.
    if (!_.has(json, "track_metadata.additional_info.recording_msid")) {
      if ("recording_msid" in json) {
        _.merge(json, {
          track_metadata: {
            additional_info: { recording_msid: json.recording_msid },
          },
        });
        delete json.recording_msid;
      } else {
        // eslint-disable-next-line no-console
        console.debug(
          "Could not find recording_msid in following json: ",
          json
        );
        return null;
      }
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error);
    return null;
  }

  // The websocket message received contain some keys which are are either duplicates or are not required in the frontend.
  // Ideally this should be handled server-side and this will probably be fixed with protobuf move.
  return json as Listen;
};

// recieves or unix epoch timestamp int or ISO datetime string
const preciseTimestamp = (
  listened_at: number | string,
  displaySetting?: "timeAgo" | "includeYear" | "excludeYear"
): string => {
  const listenDate: Date = new Date(listened_at);
  let display = displaySetting;

  // invalid date
  if (Number.isNaN(listenDate.getTime())) {
    return String(listened_at);
  }

  // determine which display setting based on time difference to use if no argument was provided
  if (!display) {
    // We can easily mock Date.now in our tests to mock the current dateTime
    const now = Date.now();
    const currentDate = new Date(now);
    const currentYear = currentDate.getFullYear();
    const listenYear = listenDate.getFullYear();
    // Date is today : format using timeago
    if (
      currentDate.getDate() === listenDate.getDate() &&
      currentDate.getMonth() === listenDate.getMonth() &&
      currentYear === listenYear
    ) {
      display = "timeAgo";
    }
    // Date is this current year, don't show the year
    else if (currentYear === listenYear) {
      display = "excludeYear";
    }
    // Not this year, show the year
    else {
      display = "includeYear";
    }
  }

  switch (display) {
    case "includeYear":
      return `${listenDate.toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "numeric",
      })}`;
    case "excludeYear":
      return `${listenDate.toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        hour: "numeric",
        minute: "numeric",
      })}`;
    default:
      return `${timeago.ago(listened_at)}`;
  }
};
// recieves or unix epoch timestamp int or ISO datetime string
const fullLocalizedDateFromTimestampOrISODate = (
  unix_epoch_timestamp: number | string | undefined | null
): string => {
  if (!unix_epoch_timestamp) {
    return "";
  }
  const date: Date = new Date(unix_epoch_timestamp);

  // invalid date
  if (Number.isNaN(date.getTime())) {
    return String(unix_epoch_timestamp);
  }
  return date.toLocaleString(undefined, {
    // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
    dateStyle: "full",
    timeStyle: "long",
  });
};

const convertDateToUnixTimestamp = (date: Date): number => {
  const newDate = new Date(date);
  const timestampInMs = newDate.getTime();
  const unixTimestamp = Math.floor(newDate.getTime() / 1000);
  return unixTimestamp;
};

/** Loads a script asynchronously into the HTML page */
export function loadScriptAsync(document: any, scriptSrc: string): void {
  const el = document.createElement("script");
  const container = document.head || document.body;
  el.type = "text/javascript";
  el.async = true;
  el.src = scriptSrc;
  container.appendChild(el);
}
export async function fetchMusicBrainzGenres() {
  // Fetch and save the list of MusicBrainz genres
  try {
    const response = await fetch(
      "https://musicbrainz.org/ws/2/genre/all?fmt=txt"
    );
    const genresList = await response.text();
    const fetchedGenres = Array.from(genresList.split("\n"));
    if (fetchedGenres.length) {
      localStorage?.setItem(
        "musicbrainz-genres",
        JSON.stringify({
          creation_date: Date.now(),
          genre_list: fetchedGenres,
        })
      );
      return fetchedGenres;
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error);
  }
  return [];
}

async function getOrFetchMBGenres(forceExpiry = false) {
  // Try to load genres from local storage, fetch them otherwise
  const localStorageString = localStorage?.getItem("musicbrainz-genres");
  if (!localStorageString) {
    // nothing saved, fetch the genres and save them
    const fetchedGenres = await fetchMusicBrainzGenres();
    return fetchedGenres;
  }
  const localStorageObject = JSON.parse(localStorageString);
  // expire the list after 2 weeks
  if (
    forceExpiry ||
    !localStorageObject ||
    Date.now() > localStorageObject.creation_date + 1209000000
  ) {
    // If the item is expired, fetch them afresh and save them
    const fetchedGenres = await fetchMusicBrainzGenres();
    return fetchedGenres;
  }
  return localStorageObject.genre_list;
}

type SentryProps = {
  sentry_dsn: string;
  sentry_traces_sample_rate?: number;
};
type GlobalAppProps = {
  api_url: string;
  websockets_url: string;
  current_user: ListenBrainzUser;
  spotify?: SpotifyUser;
  youtube?: YoutubeUser;
  soundcloud?: SoundCloudUser;
  critiquebrainz?: MetaBrainzProjectUser;
  musicbrainz?: MetaBrainzProjectUser;
  user_preferences?: UserPreferences;
};
type GlobalProps = GlobalAppProps & SentryProps;

const getPageProps = async (): Promise<{
  domContainer: HTMLElement;
  reactProps: Record<string, any>;
  sentryProps: SentryProps;
  globalAppContext: GlobalAppContextT;
}> => {
  let domContainer = document.getElementById("react-container");
  const propsElement = document.getElementById("page-react-props");
  const globalPropsElement = document.getElementById("global-react-props");
  let reactProps = {};
  let globalReactProps = {} as GlobalProps;
  let sentryProps = {} as SentryProps;
  let globalAppContext = {} as GlobalAppContextT;
  if (!domContainer) {
    // Ensure there is a container for React rendering
    // We should always have on on the page already, but displaying errors to the user relies on there being one
    domContainer = document.createElement("div");
    domContainer.id = "react-container";
    const container = document.getElementsByClassName("wrapper");
    container[0].appendChild(domContainer);
  }
  try {
    // Global props *cannot* be empty
    if (globalPropsElement?.innerHTML) {
      globalReactProps = JSON.parse(globalPropsElement.innerHTML);
    } else {
      throw new Error("No global props element found on the page");
    }
    // Page props can be empty
    if (propsElement?.innerHTML) {
      reactProps = JSON.parse(propsElement!.innerHTML);
    }

    const {
      current_user,
      api_url,
      websockets_url,
      spotify,
      youtube,
      soundcloud,
      critiquebrainz,
      musicbrainz,
      sentry_traces_sample_rate,
      sentry_dsn,
    } = globalReactProps;

    let { user_preferences } = globalReactProps;

    user_preferences = { ...user_preferences, saveData: false };

    if ("connection" in navigator) {
      // @ts-ignore
      if (navigator.connection?.saveData === true) {
        user_preferences.saveData = true;
      }
    }

    const apiService = new APIServiceClass(
      api_url || `${window.location.origin}/1`
    );
    globalAppContext = {
      APIService: apiService,
      websocketsUrl: websockets_url,
      currentUser: current_user,
      spotifyAuth: spotify,
      youtubeAuth: youtube,
      soundcloudAuth: soundcloud,
      critiquebrainzAuth: critiquebrainz,
      musicbrainzAuth: {
        ...musicbrainz,
        refreshMBToken: async function refreshMBToken() {
          try {
            const newToken = await apiService.refreshMusicbrainzToken();
            _.set(globalAppContext, "musicbrainzAuth.access_token", newToken);
          } catch (err) {
            // eslint-disable-next-line no-console
            console.error(
              "Could not refresh MusicBrainz auth token:",
              err.toString()
            );
          }
        },
      },
      userPreferences: user_preferences,
      musicbrainzGenres: await getOrFetchMBGenres(),
      recordingFeedbackManager: new RecordingFeedbackManager(
        apiService,
        current_user
      ),
    };
    sentryProps = {
      sentry_dsn,
      sentry_traces_sample_rate,
    };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error(err);
    // Show error to the user and ask to reload page
    const errorMessage = `Please refresh the page.
	If the problem persists, please contact us.
	Reason: ${err}`;
    toast.error(
      <ToastMsg title="Error loading the Page" message={errorMessage} />,
      { toastId: "page-load-error" }
    );
  }
  return {
    domContainer,
    reactProps,
    sentryProps,
    globalAppContext,
  };
};

const getListenablePin = (pinnedRecording: PinnedRecording): Listen => {
  const pinnedRecListen: Listen = {
    listened_at: 0,
    ...pinnedRecording,
  };
  _.set(
    pinnedRecListen,
    "track_metadata.additional_info.recording_msid",
    pinnedRecording.recording_msid
  );
  return pinnedRecListen;
};

const countWords = (str: string): number => {
  // Credit goes to iamwhitebox https://stackoverflow.com/a/39125279/14911205
  const words = str.match(/\w+/g);
  if (words === null) return 0;
  return words.length;
};

const handleNavigationClickEvent = (event?: React.MouseEvent): void => {
  // Allow opening in new tab or window with shift or control key
  // Otherwise prevent default
  if (event && !event.ctrlKey && !event.shiftKey) {
    event.preventDefault();
  }
};

const pinnedRecordingToListen = (pinnedRecording: PinnedRecording): Listen => {
  return {
    listened_at: pinnedRecording.created,
    track_metadata: pinnedRecording.track_metadata,
  };
};

const generateAlbumArtThumbnailLink = (
  caaId: number | string,
  releaseMBID: string,
  size: CAAThumbnailSizes = 250
): string => {
  return `https://archive.org/download/mbid-${releaseMBID}/mbid-${releaseMBID}-${caaId}_thumb${size}.jpg`;
};

export type CAAThumbnailSizes = 250 | 500 | 1200 | "small" | "large";

const getThumbnailFromCAAResponse = (
  body: CoverArtArchiveResponse,
  size: CAAThumbnailSizes = 250
): string | undefined => {
  if (!body.images?.length) {
    return undefined;
  }
  const { release } = body;
  const regexp = /musicbrainz.org\/release\/(?<mbid>[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12})/g;
  const releaseMBID = regexp.exec(release)?.groups?.mbid;

  const frontImage = body.images.find((image) => image.front);

  if (frontImage?.id && releaseMBID) {
    // CAA links are http redirects instead of https, causing LB-1067 (mixed content warning).
    // We also don't need or want the redirect from CAA, instead we can reconstruct
    // the link to the underlying archive.org resource directly
    // Also see https://github.com/metabrainz/listenbrainz-server/commit/9e40ad440d0b280b6c53d13e804f911657469c8b
    const { id } = frontImage;
    return generateAlbumArtThumbnailLink(id, releaseMBID);
  }

  // No front image? Fallback to whatever the first image is
  const { thumbnails, image } = body.images[0];
  return thumbnails[size] ?? thumbnails.small ?? image;
};

const retryParams = {
  retries: 4,
  retryOn: [429],
  retryDelay(attempt: number) {
    // Exponential backoff at random interval between maxRetryTime and minRetryTime,
    // adding minRetryTime for every attempt. `attempt` starts at 0
    const maxRetryTime = 2500;
    const minRetryTime = 1800;
    const clampedRandomTime =
      Math.random() * (maxRetryTime - minRetryTime) + minRetryTime;
    // Make it exponential
    return Math.floor(clampedRandomTime) * 2 ** attempt;
  },
};

const getAlbumArtFromReleaseGroupMBID = async (
  releaseGroupMBID: string,
  optionalSize?: CAAThumbnailSizes
): Promise<string | undefined> => {
  try {
    const CAAResponse = await fetchWithRetry(
      `https://coverartarchive.org/release-group/${releaseGroupMBID}`,
      retryParams
    );
    if (CAAResponse.ok) {
      const body: CoverArtArchiveResponse = await CAAResponse.json();
      return getThumbnailFromCAAResponse(body, optionalSize);
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn(
      `Couldn't fetch Cover Art Archive entry for ${releaseGroupMBID}`,
      error
    );
  }
  return undefined;
};

const getAlbumArtFromReleaseMBID = async (
  userSubmittedReleaseMBID: string,
  useReleaseGroupFallback: boolean | string = false,
  APIService?: APIServiceClass,
  optionalSize?: CAAThumbnailSizes
): Promise<string | undefined> => {
  try {
    const CAAResponse = await fetchWithRetry(
      `https://coverartarchive.org/release/${userSubmittedReleaseMBID}`,
      retryParams
    );
    if (CAAResponse.ok) {
      const body: CoverArtArchiveResponse = await CAAResponse.json();
      return getThumbnailFromCAAResponse(body, optionalSize);
    }

    if (CAAResponse.status === 404 && useReleaseGroupFallback) {
      let releaseGroupMBID = useReleaseGroupFallback;
      if (!_.isString(useReleaseGroupFallback) && APIService) {
        const releaseGroupResponse = await APIService.lookupMBRelease(
          userSubmittedReleaseMBID
        );
        releaseGroupMBID = releaseGroupResponse["release-group"].id;
      }
      if (!_.isString(releaseGroupMBID)) {
        return undefined;
      }

      return await getAlbumArtFromReleaseGroupMBID(releaseGroupMBID);
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn(
      `Couldn't fetch Cover Art Archive entry for ${userSubmittedReleaseMBID}`,
      error
    );
  }
  return undefined;
};

const getAlbumArtFromListenMetadata = async (
  listen: BaseListenFormat,
  spotifyUser?: SpotifyUser,
  APIService?: APIServiceClass
): Promise<string | undefined> => {
  // if spotifyListen
  if (
    SpotifyPlayer.isListenFromThisService(listen) &&
    SpotifyPlayer.hasPermissions(spotifyUser)
  ) {
    const trackID = SpotifyPlayer.getSpotifyTrackIDFromListen(listen);
    return new SpotifyAPIService(spotifyUser).getAlbumArtFromSpotifyTrackID(
      trackID
    );
  }
  if (YoutubePlayer.isListenFromThisService(listen)) {
    const videoId = YoutubePlayer.getVideoIDFromListen(listen);
    const images = YoutubePlayer.getThumbnailsFromVideoid(videoId);
    return images?.[0].src;
  }
  /** Could not load image from music service, fetching from CoverArtArchive if MBID is available */
  // directly access additional_info.release_mbid instead of using getReleaseMBID because we only want
  // to query CAA for user submitted mbids.
  const userSubmittedReleaseMBID =
    listen.track_metadata?.additional_info?.release_mbid;
  const caaId = listen.track_metadata?.mbid_mapping?.caa_id;
  const caaReleaseMbid = listen.track_metadata?.mbid_mapping?.caa_release_mbid;
  if (userSubmittedReleaseMBID) {
    // try getting the cover art using user submitted release mbid. if user submitted release mbid
    // does not have a cover art and the mapper matched to a different release, try to fallback to
    // release group cover art of the user submitted release mbid next
    const userSubmittedReleaseAlbumArt = await getAlbumArtFromReleaseMBID(
      userSubmittedReleaseMBID,
      Boolean(caaReleaseMbid) && userSubmittedReleaseMBID !== caaReleaseMbid,
      APIService
    );
    if (userSubmittedReleaseAlbumArt) {
      return userSubmittedReleaseAlbumArt;
    }
  }
  // user submitted release mbids not found, check if there is a match from mbid mapper.
  if (caaId && caaReleaseMbid) {
    return generateAlbumArtThumbnailLink(caaId, caaReleaseMbid);
  }
  return undefined;
};

/** Courtesy of Matt Zimmerman
 * https://codepen.io/influxweb/pen/LpoXba
 */
/* eslint-disable no-bitwise */
function getAverageRGBOfImage(
  imgEl: HTMLImageElement | null
): { r: number; g: number; b: number } {
  const defaultRGB = { r: 0, g: 0, b: 0 }; // for non-supporting envs
  if (!imgEl) {
    return defaultRGB;
  }
  const blockSize = 5; // only visit every 5 pixels
  const canvas = document.createElement("canvas");
  const context = canvas.getContext && canvas.getContext("2d");
  let data;
  let i = -4;
  const rgb = { r: 0, g: 0, b: 0 };
  let count = 0;

  if (!context) {
    return defaultRGB;
  }

  const height = imgEl.naturalHeight || imgEl.offsetHeight || imgEl.height;
  const width = imgEl.naturalWidth || imgEl.offsetWidth || imgEl.width;
  canvas.height = height;
  canvas.width = width;
  context.drawImage(imgEl, 0, 0);

  try {
    data = context.getImageData(0, 0, width, height);
  } catch (e) {
    /* security error, img on diff domain */
    return defaultRGB;
  }

  const { length } = data.data;

  // eslint-disable-next-line no-cond-assign
  while ((i += blockSize * 4) < length) {
    count += 1;
    rgb.r += data.data[i];
    rgb.g += data.data[i + 1];
    rgb.b += data.data[i + 2];
  }

  // ~~ used to floor values
  rgb.r = ~~(rgb.r / count);
  rgb.g = ~~(rgb.g / count);
  rgb.b = ~~(rgb.b / count);

  return rgb;
}
/* eslint-enable no-bitwise */

export function feedReviewEventToListen(
  eventMetadata: CritiqueBrainzReview
): BaseListenFormat {
  const { entity_id, entity_name, entity_type } = eventMetadata;

  let trackName;
  let artistName;
  let releaseGroupName;
  let artist_mbids: string[] = [];
  let recording_mbid;
  let release_group_mbid;
  if (entity_type === "artist" && entity_id) {
    artistName = entity_name;
    artist_mbids = [entity_id] as string[];
  }
  if (entity_type === "release_group" && entity_id) {
    // currently releaseGroupName isn't displayed by the ListenCard
    // so also assign trackName and recording_mbid
    trackName = entity_name;
    recording_mbid = entity_id;
    releaseGroupName = entity_name;
    release_group_mbid = entity_id;
  }
  if (entity_type === "recording" && entity_id) {
    trackName = entity_name;
    recording_mbid = entity_id;
  }
  return {
    listened_at: -1,
    track_metadata: {
      track_name: trackName ?? "",
      artist_name: artistName ?? "",
      release_name: releaseGroupName ?? "",
      additional_info: {
        artist_mbids,
        recording_mbid,
        release_group_mbid,
      },
    },
  };
}

export function personalRecommendationEventToListen(
  eventMetadata: UserTrackPersonalRecommendationMetadata
): BaseListenFormat {
  return {
    listened_at: -1,
    track_metadata: eventMetadata.track_metadata,
  } as BaseListenFormat;
}

export function getReviewEventContent(
  eventMetadata: CritiqueBrainzReview | CritiqueBrainzReviewAPI
): JSX.Element {
  const additionalContent = getAdditionalContent(
    eventMetadata as CritiqueBrainzReview
  );
  const reviewID =
    _.get(eventMetadata, "review_mbid") ?? _.get(eventMetadata, "id");
  const userName =
    _.get(eventMetadata, "user_name") ??
    _.get(eventMetadata, "user.display_name");
  return (
    <div className="review">
      {!isUndefined(eventMetadata.rating) && isFinite(eventMetadata.rating) && (
        <div className="rating-container">
          <b>Rating: </b>
          <Rating
            readonly
            onClick={() => {}}
            className="rating-stars"
            ratingValue={eventMetadata.rating}
            transition
            size={20}
            iconsCount={5}
          />
        </div>
      )}
      <div className="text">
        <ReactMarkdown
          disallowedElements={["h1", "h2", "h3", "h4", "h5", "h6"]}
          unwrapDisallowed
        >
          {additionalContent}
        </ReactMarkdown>
      </div>
      <div className="author read-more">
        by {userName}
        <a
          href={`https://critiquebrainz.org/review/${reviewID}`}
          target="_blank"
          rel="noopener noreferrer"
          className="pull-right"
        >
          Read on CritiqueBrainz
        </a>
      </div>
    </div>
  );
}

export function getPersonalRecommendationEventContent(
  eventMetadata: UserTrackPersonalRecommendationMetadata,
  isCreator: Boolean
): JSX.Element {
  const additionalContent = getAdditionalContent(eventMetadata);
  return (
    <>
      {isCreator && (
        <div className="sent-to">
          Sent to:{" "}
          {eventMetadata.users.map((userName) => {
            return <NamePill title={userName} />;
          })}
        </div>
      )}
      {additionalContent}
    </>
  );
}

export {
  searchForSpotifyTrack,
  searchForSoundcloudTrack,
  getMBIDMappingArtistLink,
  getStatsArtistLink,
  getArtistLink,
  getTrackLink,
  formatWSMessageToListen,
  preciseTimestamp,
  fullLocalizedDateFromTimestampOrISODate,
  convertDateToUnixTimestamp,
  getPageProps,
  searchForYoutubeTrack,
  getListenablePin,
  countWords,
  handleNavigationClickEvent,
  getRecordingMSID,
  getRecordingMBID,
  getReleaseMBID,
  getReleaseGroupMBID,
  getArtistMBIDs,
  getArtistName,
  getTrackName,
  getReleaseName,
  getTrackDurationInMs,
  getListenCardKey,
  pinnedRecordingToListen,
  getAlbumArtFromReleaseMBID,
  getAlbumArtFromReleaseGroupMBID,
  getAlbumArtFromListenMetadata,
  getAverageRGBOfImage,
  getAdditionalContent,
  generateAlbumArtThumbnailLink,
};
