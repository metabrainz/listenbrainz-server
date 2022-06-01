import * as React from "react";
import * as _ from "lodash";
import * as timeago from "time-ago";
import { isFinite, isUndefined } from "lodash";
import { Rating } from "react-simple-star-rating";
import SpotifyPlayer from "../brainzplayer/SpotifyPlayer";
import YoutubePlayer from "../brainzplayer/YoutubePlayer";
import SpotifyAPIService from "./SpotifyAPIService";

const searchForSpotifyTrack = async (
  spotifyToken?: string,
  trackName?: string,
  artistName?: string,
  releaseName?: string
): Promise<SpotifyTrack | null> => {
  if (!spotifyToken) {
    throw new Error(
      JSON.stringify({
        status: 403,
        message: "You need to connect to your Spotify account",
      })
    );
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

  const responseBody = await response.json();
  if (!response.ok) {
    throw responseBody.error;
  }
  const tracks: Array<any> = _.get(responseBody, "items");
  const videoIds = tracks.map((track) => track.id.videoId);
  if (videoIds.length) return videoIds;
  return null;
};

const getAdditionalContent = (metadata: EventMetadata): string =>
  _.get(metadata, "blurb_content") ?? _.get(metadata, "text") ?? "";

const getArtistMBIDs = (listen: Listen): string[] | undefined =>
  _.get(listen, "track_metadata.additional_info.artist_mbids") ??
  _.get(listen, "track_metadata.mbid_mapping.artist_mbids");

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

const getTrackName = (listen?: Listen | JSPFTrack | PinnedRecording): string =>
  _.get(listen, "track_metadata.track_name", "") || _.get(listen, "title", "");

const getTrackDuration = (listen?: Listen | JSPFTrack): number =>
  _.get(listen, "track_metadata.additional_info.duration_ms", "") ||
  _.get(listen, "duration", "");

const getArtistName = (listen?: Listen | JSPFTrack | PinnedRecording): string =>
  _.get(listen, "track_metadata.artist_name", "") ||
  _.get(listen, "creator", "");

const getArtistLink = (listen: Listen) => {
  const artistName = getArtistName(listen);
  const artistMbids = getArtistMBIDs(listen);
  const firstArtist = _.first(artistMbids);
  if (firstArtist) {
    return (
      <a
        href={`https://musicbrainz.org/artist/${firstArtist}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {artistName}
      </a>
    );
  }
  return artistName;
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
        hour12: true,
      })}`;
    case "excludeYear":
      return `${listenDate.toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
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

/** Loads a script asynchronously into the HTML page */
export function loadScriptAsync(document: any, scriptSrc: string): void {
  const el = document.createElement("script");
  const container = document.head || document.body;
  el.type = "text/javascript";
  el.async = true;
  el.src = scriptSrc;
  container.appendChild(el);
}

const createAlert = (
  type: AlertType,
  title: string,
  message: string | JSX.Element
): Alert => {
  return {
    id: new Date().getTime(),
    type,
    headline: title,
    message,
  };
};

interface GlobalProps {
  api_url: string;
  sentry_dsn: string;
  current_user: ListenBrainzUser;
  spotify?: SpotifyUser;
  youtube?: YoutubeUser;
  critiquebrainz?: CritiqueBrainzUser;
  sentry_traces_sample_rate?: number;
}

const getPageProps = (): {
  domContainer: HTMLElement;
  reactProps: Record<string, any>;
  globalReactProps: GlobalProps;
  optionalAlerts: Alert[];
} => {
  let domContainer = document.getElementById("react-container");
  const propsElement = document.getElementById("page-react-props");
  const globalPropsElement = document.getElementById("global-react-props");
  let reactProps = {};
  let globalReactProps = {} as GlobalProps;
  const optionalAlerts = [];
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
  } catch (err) {
    // Show error to the user and ask to reload page
    const errorMessage = `Please refresh the page.
	If the problem persists, please contact us.
	Reason: ${err}`;
    const newAlert = createAlert(
      "danger",
      "Error loading the page",
      errorMessage
    );
    optionalAlerts.push(newAlert);
  }
  return { domContainer, reactProps, globalReactProps, optionalAlerts };
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

const getAlbumArtFromListenMetadata = async (
  listen: BaseListenFormat,
  spotifyUser?: SpotifyUser
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
  const releaseMBID = getReleaseMBID(listen);
  if (releaseMBID) {
    try {
      const CAAResponse = await fetch(
        `https://coverartarchive.org/release/${releaseMBID}`
      );
      if (CAAResponse.ok) {
        const body: CoverArtArchiveResponse = await CAAResponse.json();
        if (!body.images?.[0]?.thumbnails) {
          return undefined;
        }
        const { thumbnails } = body.images[0];
        return (
          thumbnails[250] ??
          thumbnails.small ??
          // If neither of the above exists, return the first one we find
          // @ts-ignore
          thumbnails[Object.keys(thumbnails)?.[0]]
        );
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.warn(
        `Couldn't fetch Cover Art Archive entry for ${releaseMBID}`,
        error
      );
    }
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

export function getReviewEventContent(
  eventMetadata: CritiqueBrainzReview
): JSX.Element {
  const additionalContent = getAdditionalContent(eventMetadata);
  return (
    <>
      <a
        href={`https://critiquebrainz.org/review/${eventMetadata.review_mbid}`}
        target="_blank"
        rel="noopener noreferrer"
        className="pull-right"
      >
        See this review on CritiqueBrainz
      </a>
      {!isUndefined(eventMetadata.rating) && isFinite(eventMetadata.rating) && (
        <div className="rating-container">
          <b>Rating: </b>
          <Rating
            readonly
            onClick={() => {}}
            className="rating-stars"
            ratingValue={eventMetadata.rating * 20} // CB stores ratings in 0 - 5 scale but the component requires 0 - 100
            transition
            size={20}
            iconsCount={5}
          />
        </div>
      )}
      {additionalContent}
    </>
  );
}

export {
  searchForSpotifyTrack,
  getArtistLink,
  getTrackLink,
  formatWSMessageToListen,
  preciseTimestamp,
  fullLocalizedDateFromTimestampOrISODate,
  getPageProps,
  searchForYoutubeTrack,
  createAlert,
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
  getTrackDuration,
  pinnedRecordingToListen,
  getAlbumArtFromListenMetadata,
  getAverageRGBOfImage,
  getAdditionalContent,
};
